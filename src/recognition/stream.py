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

import re
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


# Strip leading/trailing punctuation for word equality during agreement.
# Whisper's output varies (",", ".", capitalisation) across rounds even on
# identical audio — normalising lets us compare at the lexical level while
# still emitting the model's chosen punctuation in the committed text.
_WORD_NORM_RE = re.compile(r"[^\w']+", re.UNICODE)

# Minimum words before a commit is allowed to land into the user's text,
# unless (a) the agreed prefix ends in terminal punctuation, or (b) the
# whole new-content has agreed (no tentative remainder, so the short
# fragment is definitely the user's complete utterance, not a transient
# prefix of something longer). Without this gate, K=2 fires on single-word
# prefix agreements ("I", "And", "Missing") that read as dribble between
# bigger commits.
MIN_COMMIT_WORDS = 2
_TERMINAL_PUNCTUATION = (".", "!", "?")


def _normalise_word(w: str) -> str:
    return _WORD_NORM_RE.sub("", w).lower()


class CommitTracker:
    """LocalAgreement-K commit logic over per-round word sequences.

    A word is *committed* the first time it appears at the same position
    (relative to the committed prefix) in K consecutive rounds. Until
    committed, words are *tentative* — visible to the UI but not injected.

    Algorithm per update():
      1. Align: find the longest suffix of the committed text that is a
         prefix of the new round. That overlap is the part of the audio
         we've already finalised; everything after is "new content".
      2. Within the new content, compute the longest common prefix with
         the previous round's new content (case- & punctuation-insensitive).
      3. That common prefix advances commitment. Anything beyond is tentative.

    K is fixed at 2 for v1 — well-supported in the literature for
    streaming Whisper and avoids the latency hit of K=3.

    Caveats:
      - Word-level only; we don't track per-token timestamps. This is
        sufficient for dictation-length sessions where the rolling
        window typically still contains the start of the utterance.
      - When the window slides past previously committed audio, alignment
        falls through to 0 (no overlap) and we restart agreement from
        scratch on the new content. Safe but conservative.
    """

    def __init__(self) -> None:
        self._committed_words: list[str] = []
        # Store the full previous round, not just its "new content" — the
        # committed prefix grows between rounds, so we have to recompute
        # each round's post-commit slice against the LATEST committed state.
        self._prev_round_words: list[str] = []

    @property
    def committed_text(self) -> str:
        return " ".join(self._committed_words)

    def reset(self) -> None:
        self._committed_words.clear()
        self._prev_round_words.clear()

    def update(self, round_words: list[str]) -> tuple[str, str]:
        """Feed one round's words; return (newly_committed, tentative)."""
        if not round_words:
            self._prev_round_words = []
            return ("", "")

        # New content for THIS round: trim the committed-prefix overlap
        new_content = round_words[self._align(round_words):]

        # New content for the PREVIOUS round, computed against the SAME
        # committed state so the two slices are directly comparable.
        prev_new_content = self._prev_round_words[self._align(self._prev_round_words):]

        # LocalAgreement: words that agreed across two consecutive rounds
        common = self._common_prefix(new_content, prev_new_content)

        # Hold back fragments shorter than MIN_COMMIT_WORDS that don't end
        # at a sentence boundary AND have more tentative content following.
        # The tentative-non-empty check is the key: if everything has
        # agreed (tentative is empty), the short fragment IS the user's
        # complete utterance — commit it. Otherwise it's a transient
        # prefix of something still being decoded — wait for more.
        if 0 < len(common) < MIN_COMMIT_WORDS and len(common) < len(new_content):
            last = common[-1].rstrip()
            if not last.endswith(_TERMINAL_PUNCTUATION):
                common = []

        # Commit using the CURRENT round's casing/punctuation
        newly_committed_words = new_content[: len(common)]
        if newly_committed_words:
            self._committed_words.extend(newly_committed_words)

        tentative_words = new_content[len(common):]

        # Stash full round for next call
        self._prev_round_words = round_words

        return (" ".join(newly_committed_words), " ".join(tentative_words))

    def _align(self, round_words: list[str]) -> int:
        """Index in round_words where 'new content' begins.

        Returns the size of the matched committed-tail / round-head.
        """
        if not self._committed_words:
            return 0
        committed_norm = [_normalise_word(w) for w in self._committed_words]
        round_norm = [_normalise_word(w) for w in round_words]
        max_k = min(len(committed_norm), len(round_norm))
        for k in range(max_k, 0, -1):
            if round_norm[:k] == committed_norm[-k:]:
                return k
        return 0

    @staticmethod
    def _common_prefix(a: list[str], b: list[str]) -> list[str]:
        """Longest common prefix using normalised comparison."""
        out: list[str] = []
        for x, y in zip(a, b):
            if _normalise_word(x) == _normalise_word(y) and _normalise_word(x):
                out.append(x)
            else:
                break
        return out


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
        on_committed: Callable[[str], None] | None = None,
        on_tentative: Callable[[str], None] | None = None,
    ) -> None:
        self._recognizer = recognizer
        self._sample_rate = sample_rate
        self._window_seconds = window_seconds
        self._interval_seconds = interval_seconds
        self._language = language
        self._initial_prompt = initial_prompt
        self._vad_min_silence_ms = vad_min_silence_ms
        self._on_segments = on_segments
        self._on_committed = on_committed  # called with newly-committed text per round
        self._on_tentative = on_tentative  # called with current tentative tail per round

        # Buffer of float32 chunks; protected by lock.
        self._chunks: deque[np.ndarray] = deque()
        self._buffer_samples = 0  # cached total length, kept in sync with deque
        self._max_samples = int(self._sample_rate * self._window_seconds * 1.5)
        self._lock = threading.Lock()

        # Commit tracker (LocalAgreement-K word-prefix)
        self._commit_tracker = CommitTracker()

        # Worker control
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        # Pause flag: when True, the worker still wakes on its interval but
        # skips the transcribe call. Audio keeps flowing into the buffer
        # (so pause→resume doesn't lose context). Driven by app-level VAD.
        self._paused = False
        self._round = 0

    def start(self) -> None:
        """Spawn the worker thread. Idempotent."""
        if self._worker and self._worker.is_alive():
            return
        self._stop_event.clear()
        self._round = 0
        self._commit_tracker.reset()
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
        """Signal worker to exit. Returns within ~500ms even if a Whisper
        round is mid-flight — the daemon worker will exit naturally once
        its current call returns. Caller MUST also detach any callbacks
        BEFORE calling stop() if it wants to be sure no late callbacks
        fire after stop returns.
        """
        self._stop_event.set()
        if self._worker:
            # Short timeout so we don't freeze the Qt main thread while a
            # transcribe round is finishing. Worker is a daemon and will
            # exit on its own after its current call returns.
            self._worker.join(timeout=0.5)
            if self._worker.is_alive():
                logger.debug("Worker still mid-round at stop; daemon will exit later")
            self._worker = None
        with self._lock:
            self._chunks.clear()
            self._buffer_samples = 0
        logger.info("Streaming transcriber stopped (rounds_run=%d)", self._round)

    def pause(self) -> None:
        """Skip future transcription rounds until resume() is called.

        Idempotent. The audio buffer continues to fill so resume() picks up
        with full context. Whisper hallucinations on long silences are
        avoided because no rounds run during silence.
        """
        if not self._paused:
            self._paused = True
            logger.info("Streaming paused (silence detected)")

    def resume(self) -> None:
        """Resume transcription rounds after pause()."""
        if self._paused:
            self._paused = False
            logger.info("Streaming resumed (speech detected)")

    @property
    def is_paused(self) -> bool:
        return self._paused

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

    # Minimum buffered audio before we even attempt a transcription round.
    # Whisper hallucinates aggressively on very short clips and the
    # LocalAgreement K=2 commit can lock in a hallucination if the model
    # produces the SAME garbage twice. 1.5s gives the audio enough body
    # that real-speech rounds dominate over hallucinations.
    _MIN_BUFFER_SECONDS = 1.5

    def _snapshot_window(self) -> np.ndarray | None:
        """Concatenate the last window_seconds of audio into a single array.

        Returns None if there isn't enough audio yet (under
        ``_MIN_BUFFER_SECONDS``) — better latency floor than commit risk.
        """
        target = int(self._sample_rate * self._window_seconds)
        with self._lock:
            if self._buffer_samples < int(self._sample_rate * self._MIN_BUFFER_SECONDS):
                return None
            joined = np.concatenate(list(self._chunks))
        if joined.size > target:
            joined = joined[-target:]
        return joined

    def _run(self) -> None:
        """Worker loop: schedule rounds at fixed interval boundaries.

        Old loop did wait(interval) THEN transcribe — total cycle was
        (interval + transcribe_time) ~= 1.7s for 1s interval + 0.7s tiny.
        New loop sleeps until next_round_time so cycles are exactly
        interval_seconds apart when transcription fits, and just go
        back-to-back when transcription is slower (graceful degradation,
        no queue buildup).
        """
        next_round_time = time.monotonic() + self._interval_seconds
        while not self._stop_event.is_set():
            # Sleep until the next scheduled round, but wake immediately if
            # stop is requested.
            now = time.monotonic()
            sleep_for = max(0.0, next_round_time - now)
            if self._stop_event.wait(timeout=sleep_for):
                break
            next_round_time += self._interval_seconds
            # If we've fallen significantly behind, snap forward to "now"
            # rather than burning through accumulated rounds.
            if next_round_time < time.monotonic():
                next_round_time = time.monotonic() + self._interval_seconds

            # Skip work entirely while paused — audio still buffers via feed(),
            # we just don't burn CPU on Whisper or risk silent-period hallucinations.
            if self._paused:
                continue

            window = self._snapshot_window()
            if window is None:
                # Still warming up the buffer (< _MIN_BUFFER_SECONDS).
                # Visible at INFO so a streaming session that produces no
                # output is diagnosable without DEBUG logs.
                logger.info("Streaming round skipped: buffer too short")
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
            logger.info(
                "Streaming round %d: %d segments in %.2fs (window=%.1fs)",
                self._round, len(segments), elapsed, window.size / self._sample_rate,
            )

            # If stop was requested while we were transcribing, swallow this
            # round — late callbacks landing after stop confuse the UI.
            if self._stop_event.is_set():
                break

            if segments and self._on_segments:
                try:
                    self._on_segments(segments)
                except Exception as e:
                    logger.exception("on_segments callback raised: %s", e)

            # LocalAgreement commit pass: turn flickery rounds into stable text.
            round_text = " ".join(s.text for s in segments).strip()
            round_words = round_text.split() if round_text else []
            newly_committed, tentative = self._commit_tracker.update(round_words)

            if newly_committed:
                logger.info("Committed: %r", newly_committed)
                if self._on_committed:
                    try:
                        self._on_committed(newly_committed)
                    except Exception as e:
                        logger.exception("on_committed raised: %s", e)
            if self._on_tentative:
                try:
                    self._on_tentative(tentative)
                except Exception as e:
                    logger.exception("on_tentative raised: %s", e)
