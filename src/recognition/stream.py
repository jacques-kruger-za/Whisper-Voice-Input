"""Streaming transcription substrate — preview + utterance-finalize architecture.

Two distinct outputs:

1. ``on_preview(text)`` fires every round with the LATEST rolling-window
   transcription. Best-effort, may flicker, may jump as Whisper revises.
   Drives a transient UI surface so the user sees something is happening.
   Raw model output, no cleanup applied.

2. ``finalize()`` is called by the app on end-of-utterance (VAD-detected
   silence after speech). Runs a fresh full-quality transcribe on the
   audio captured since the last finalize — full context, full beam
   search if the recogniser supports it. Returns the final text. THIS is
   what gets injected into the user's editor.

The preview pipeline is fast and may be wrong; the finalize pipeline is
slow but accurate. The split means we don't compromise reliability of
the committed text just to get live feedback during streaming.

Threading model:
- ``feed(chunk)`` runs on the audio thread (recorder callback). Cheap.
- A worker thread runs ``recognizer.transcribe_array`` on the rolling
  window every ``interval_seconds`` and dispatches preview text via
  ``on_preview``. Callbacks run on the worker thread; consumers must
  marshal to the UI thread (e.g. via a Qt signal).
- ``finalize()`` is called synchronously by the app on the UI thread.
  It pauses the worker briefly so the audio buffer doesn't shift under
  the final transcribe call.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Protocol

import numpy as np

from ..config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class StreamSegment:
    """One transcription segment from a single decoding round.

    Times are RELATIVE to the start of the audio window passed to
    transcribe_array — not relative to the whole streaming session.
    Text is the raw model output (no cleanup applied).
    """
    text: str
    start: float
    end: float


class _RecognizerProtocol(Protocol):
    def transcribe_array(
        self,
        samples,
        language: str | None = ...,
        initial_prompt: str | None = ...,
        vad_min_silence_ms: int = ...,
    ) -> list: ...


class StreamingTranscriber:
    """Rolling-window preview transcriber + on-demand utterance finalizer."""

    # Minimum buffered audio before we attempt the FIRST round (avoids
    # hallucinations on tiny clips).
    _MIN_BUFFER_SECONDS = 1.5

    # Hard cap on the per-utterance audio buffer (the audio kept since the
    # last finalize). Long enough for a paragraph of dictation; if exceeded
    # we drop oldest samples — better than runaway memory if a user dictates
    # for 10 minutes without a single VAD-detected pause.
    _MAX_UTTERANCE_SECONDS = 90.0

    def __init__(
        self,
        recognizer: _RecognizerProtocol,
        *,
        sample_rate: int = 16000,
        window_seconds: float = 8.0,
        interval_seconds: float = 1.0,
        language: str | None = None,
        initial_prompt: str | None = None,
        vad_min_silence_ms: int = 500,
        on_preview: Callable[[str], None] | None = None,
    ) -> None:
        self._recognizer = recognizer
        self._sample_rate = sample_rate
        self._window_seconds = window_seconds
        self._interval_seconds = interval_seconds
        self._language = language
        self._initial_prompt = initial_prompt
        self._vad_min_silence_ms = vad_min_silence_ms
        self._on_preview = on_preview

        # Rolling window buffer (used for preview rounds — bounded).
        self._chunks: deque[np.ndarray] = deque()
        self._buffer_samples = 0
        self._max_window_samples = int(self._sample_rate * self._window_seconds * 1.5)

        # Utterance buffer: ALL audio captured since the last finalize.
        # Used at finalize-time for a fresh full-context transcription so
        # the committed text is independent of any rolling-window shifts.
        self._utterance_chunks: list[np.ndarray] = []
        self._utterance_samples = 0
        self._max_utterance_samples = int(self._sample_rate * self._MAX_UTTERANCE_SECONDS)

        self._lock = threading.Lock()

        # Worker control
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._paused = False
        self._round = 0

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> None:
        """Spawn the preview worker thread. Idempotent."""
        if self._worker and self._worker.is_alive():
            return
        self._stop_event.clear()
        self._round = 0
        with self._lock:
            self._chunks.clear()
            self._buffer_samples = 0
            self._utterance_chunks = []
            self._utterance_samples = 0
        self._worker = threading.Thread(
            target=self._run, name="StreamingTranscriber", daemon=True,
        )
        self._worker.start()
        logger.info(
            "Streaming transcriber started (window=%.1fs, interval=%.1fs, vad_silence=%dms)",
            self._window_seconds, self._interval_seconds, self._vad_min_silence_ms,
        )

    def stop(self) -> None:
        """Signal worker to exit. Returns within ~500ms."""
        self._stop_event.set()
        if self._worker:
            self._worker.join(timeout=0.5)
            if self._worker.is_alive():
                logger.debug("Worker still mid-round at stop; daemon will exit later")
            self._worker = None
        with self._lock:
            self._chunks.clear()
            self._buffer_samples = 0
            self._utterance_chunks = []
            self._utterance_samples = 0
        logger.info("Streaming transcriber stopped (rounds_run=%d)", self._round)

    def pause(self) -> None:
        """Skip future preview rounds until resume(). Audio still buffers."""
        if not self._paused:
            self._paused = True
            logger.info("Streaming preview paused (silence)")

    def resume(self) -> None:
        if self._paused:
            self._paused = False
            logger.info("Streaming preview resumed (speech)")

    @property
    def is_paused(self) -> bool:
        return self._paused

    # ── Audio ingest ──────────────────────────────────────────────────────

    def feed(self, audio_chunk: np.ndarray) -> None:
        """Append audio. Thread-safe; called from the recorder thread.

        Both the rolling preview buffer AND the utterance buffer get the
        chunk. The utterance buffer keeps everything since the last
        finalize (capped at _MAX_UTTERANCE_SECONDS).
        """
        if audio_chunk.ndim != 1:
            audio_chunk = audio_chunk.reshape(-1)
        with self._lock:
            self._chunks.append(audio_chunk)
            self._buffer_samples += audio_chunk.size
            self._trim_window_locked()
            self._utterance_chunks.append(audio_chunk)
            self._utterance_samples += audio_chunk.size
            self._trim_utterance_locked()

    def _trim_window_locked(self) -> None:
        """Drop oldest rolling-window chunks past the cap."""
        while self._buffer_samples > self._max_window_samples and self._chunks:
            old = self._chunks.popleft()
            self._buffer_samples -= old.size

    def _trim_utterance_locked(self) -> None:
        """Drop oldest utterance chunks past the cap (90s default)."""
        while self._utterance_samples > self._max_utterance_samples and self._utterance_chunks:
            dropped = self._utterance_chunks.pop(0)
            self._utterance_samples -= dropped.size
            logger.warning(
                "Utterance exceeded %ds without finalize; dropping oldest %d samples",
                int(self._MAX_UTTERANCE_SECONDS), dropped.size,
            )

    # ── Finalize (called from the UI thread on end-of-utterance) ──────────

    def finalize(self) -> str:
        """Run a fresh full-context transcribe on all audio since last
        finalize. Returns clean (uncleaned) text from the recogniser.

        Calls back on the UI thread — synchronous. Internally this clears
        the utterance buffer so the next round of streaming starts fresh.
        Preview is NOT cleared automatically; the caller decides when to
        clear the preview UI.
        """
        with self._lock:
            if not self._utterance_chunks:
                return ""
            utterance = np.concatenate(self._utterance_chunks)
            self._utterance_chunks = []
            self._utterance_samples = 0

        duration = utterance.size / self._sample_rate
        logger.info("Finalize: transcribing %.2fs of utterance audio", duration)
        t0 = time.perf_counter()
        try:
            segments = self._recognizer.transcribe_array(
                utterance,
                language=self._language,
                initial_prompt=self._initial_prompt,
                vad_min_silence_ms=self._vad_min_silence_ms,
            )
        except Exception as e:
            logger.exception("Finalize transcribe failed: %s", e)
            return ""
        text = " ".join(getattr(s, "text", "").strip() for s in segments).strip()
        logger.info(
            "Finalize complete in %.2fs: %d segments, %d chars",
            time.perf_counter() - t0, len(segments), len(text),
        )
        return text

    # ── Worker loop ───────────────────────────────────────────────────────

    def _snapshot_window(self) -> np.ndarray | None:
        target = int(self._sample_rate * self._window_seconds)
        with self._lock:
            if self._buffer_samples < int(self._sample_rate * self._MIN_BUFFER_SECONDS):
                return None
            joined = np.concatenate(list(self._chunks))
        if joined.size > target:
            joined = joined[-target:]
        return joined

    def _run(self) -> None:
        """Worker loop: emit preview text every interval_seconds.

        Schedules at fixed interval boundaries so cycles land at regular
        cadence even when transcribe time varies. Falls back to back-to-back
        when behind, snaps forward when far behind.
        """
        next_round_time = time.monotonic() + self._interval_seconds
        while not self._stop_event.is_set():
            now = time.monotonic()
            sleep_for = max(0.0, next_round_time - now)
            if self._stop_event.wait(timeout=sleep_for):
                break
            next_round_time += self._interval_seconds
            if next_round_time < time.monotonic():
                next_round_time = time.monotonic() + self._interval_seconds

            if self._paused:
                continue

            window = self._snapshot_window()
            if window is None:
                logger.info("Streaming round skipped: buffer too short")
                continue

            t0 = time.perf_counter()
            try:
                # Preview rounds DELIBERATELY do not pass initial_prompt.
                # Whisper latches onto prompt words on short/weak windows
                # and repeats them ("Jeanré, Jeanré, Jeanré..."), polluting
                # the preview UI. The vocab bias still applies at finalize
                # where it matters (the committed text). Trade-off:
                # marginal preview accuracy on custom names is worse, but
                # the spam is gone and the editor still gets boosted text.
                segments = self._recognizer.transcribe_array(
                    window,
                    language=self._language,
                    initial_prompt=None,
                    vad_min_silence_ms=self._vad_min_silence_ms,
                )
            except Exception as e:
                logger.exception("Streaming round failed: %s", e)
                continue

            elapsed = time.perf_counter() - t0
            self._round += 1

            if self._stop_event.is_set():
                break

            text = " ".join(getattr(s, "text", "").strip() for s in segments).strip()
            preview = text[:120] + ("..." if len(text) > 120 else "")
            logger.info(
                "Streaming round %d: %d segs in %.2fs (window=%.1fs) text=%r",
                self._round, len(segments), elapsed,
                window.size / self._sample_rate, preview,
            )

            if self._on_preview:
                try:
                    self._on_preview(text)
                except Exception as e:
                    logger.exception("on_preview raised: %s", e)
