"""Sliding-window streaming transcription substrate (S1).

Owns a rolling audio buffer and a worker thread that transcribes the most
recent ``window_seconds`` of audio every ``interval_seconds``. Emits raw
faster-whisper Segment objects via a callback — no commit/hold-back logic
yet (that's S2). The caller decides what to do with the (potentially
flickering) per-round segments.

Threading model:
- ``feed(chunk)`` is called from the audio recorder thread; it appends to
  a deque under a lock and returns immediately.
- A single worker thread sleeps for ``interval_seconds``, snapshots the
  last ``window_seconds`` of buffered audio under the lock, runs
  ``recognizer.transcribe_array()``, and dispatches segments to
  ``on_segments``.
- ``stop()`` signals the worker via Event, joins, and clears the buffer.

Design notes:
- The buffer holds raw float32 samples (16 kHz mono). We keep slightly
  more than ``window_seconds`` worth and slice off the tail for each
  round — this is simpler than a fixed-size ring and avoids reallocation.
- VAD fires per-call inside transcribe_array with a 500ms min-silence so
  segment boundaries arrive promptly during natural pauses.
- The callback runs on the worker thread; consumers must be thread-safe
  (e.g. emit a Qt signal to the UI thread).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Iterable, Protocol

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
    """Rolling-window transcription driver."""

    def __init__(
        self,
        recognizer: _RecognizerProtocol,
        *,
        sample_rate: int = 16000,
        window_seconds: float = 12.0,
        interval_seconds: float = 1.0,
        language: str | None = None,
        initial_prompt: str | None = None,
        vad_min_silence_ms: int = 500,
        on_segments: Callable[[list[StreamSegment]], None] | None = None,
    ) -> None:
        self._recognizer = recognizer
        self._sample_rate = sample_rate
        self._window_seconds = window_seconds
        self._interval_seconds = interval_seconds
        self._language = language
        self._initial_prompt = initial_prompt
        self._vad_min_silence_ms = vad_min_silence_ms
        self._on_segments = on_segments

        # Buffer of float32 chunks; protected by lock.
        self._chunks: deque[np.ndarray] = deque()
        self._buffer_samples = 0  # cached total length, kept in sync with deque
        self._max_samples = int(self._sample_rate * self._window_seconds * 1.5)
        self._lock = threading.Lock()

        # Worker control
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._round = 0

    def start(self) -> None:
        """Spawn the worker thread. Idempotent."""
        if self._worker and self._worker.is_alive():
            return
        self._stop_event.clear()
        self._round = 0
        self._worker = threading.Thread(
            target=self._run,
            name="StreamingTranscriber",
            daemon=True,
        )
        self._worker.start()
        logger.info(
            "Streaming transcriber started (window=%.1fs, interval=%.1fs, vad_silence=%dms)",
            self._window_seconds, self._interval_seconds, self._vad_min_silence_ms,
        )

    def stop(self) -> None:
        """Signal worker to exit and join it. Drops any pending audio."""
        self._stop_event.set()
        if self._worker:
            self._worker.join(timeout=self._interval_seconds * 3)
            self._worker = None
        with self._lock:
            self._chunks.clear()
            self._buffer_samples = 0
        logger.info("Streaming transcriber stopped (rounds_run=%d)", self._round)

    def feed(self, audio_chunk: np.ndarray) -> None:
        """Append an audio chunk. Thread-safe; called from the recorder thread.

        Chunk must be float32 in -1..1 at the configured sample rate. Mono.
        Older samples are dropped automatically once the buffer exceeds the
        soft cap (1.5 × window_seconds).
        """
        if audio_chunk.ndim != 1:
            audio_chunk = audio_chunk.reshape(-1)
        with self._lock:
            self._chunks.append(audio_chunk)
            self._buffer_samples += audio_chunk.size
            self._trim_locked()

    def _trim_locked(self) -> None:
        """Drop oldest chunks until we're within max_samples. Caller holds lock."""
        while self._buffer_samples > self._max_samples and self._chunks:
            old = self._chunks.popleft()
            self._buffer_samples -= old.size

    def _snapshot_window(self) -> np.ndarray | None:
        """Concatenate the last window_seconds of audio into a single array.

        Returns None if there isn't enough audio yet to bother transcribing
        (less than 0.5 seconds — under VAD's min_speech_duration anyway).
        """
        target = int(self._sample_rate * self._window_seconds)
        with self._lock:
            if self._buffer_samples < int(self._sample_rate * 0.5):
                return None
            # Cheapest: concatenate everything, then slice tail.
            joined = np.concatenate(list(self._chunks))
        if joined.size > target:
            joined = joined[-target:]
        return joined

    def _run(self) -> None:
        """Worker loop: every interval, transcribe and emit segments."""
        while not self._stop_event.is_set():
            # Sleep first so the buffer has audio before the first round.
            if self._stop_event.wait(timeout=self._interval_seconds):
                break

            window = self._snapshot_window()
            if window is None:
                continue

            t0 = time.perf_counter()
            try:
                raw_segments = self._recognizer.transcribe_array(
                    window,
                    language=self._language,
                    initial_prompt=self._initial_prompt,
                    vad_min_silence_ms=self._vad_min_silence_ms,
                )
            except Exception as e:
                logger.exception("Streaming round failed: %s", e)
                continue

            elapsed = time.perf_counter() - t0
            self._round += 1
            segments = [
                StreamSegment(
                    text=s.text.strip(),
                    start=getattr(s, "start", 0.0) or 0.0,
                    end=getattr(s, "end", 0.0) or 0.0,
                )
                for s in raw_segments
                if (s.text or "").strip()
            ]
            logger.debug(
                "Streaming round %d: %d segments in %.2fs (window=%.2fs)",
                self._round, len(segments), elapsed, window.size / self._sample_rate,
            )

            if segments and self._on_segments:
                try:
                    self._on_segments(segments)
                except Exception as e:
                    logger.exception("on_segments callback raised: %s", e)
