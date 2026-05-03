"""Audio-silence tracker for VAD-driven session lifecycle.

Fed by the recorder's level callback (audio thread). Polled by the UI thread
to drive auto-pause / auto-stop transitions for both streaming dictation and
command capture.

Thread model:
- ``update(level)`` is called from the audio thread. Cheap — just compares
  against a threshold and stamps a monotonic timestamp under a lock.
- ``silence_duration()`` / ``speech_detected()`` / ``elapsed_since_start()``
  are called from the UI thread (typically a 200ms QTimer).

Times are in seconds (monotonic clock). The monitor is reset between
sessions via ``reset()``; the active modality decides what thresholds to
apply against the duration values.
"""

from __future__ import annotations

import threading
import time

from ..config.constants import SILENCE_THRESHOLD


class SilenceMonitor:
    """Track silence durations relative to a session start and last loud sample."""

    def __init__(self, level_threshold: float = SILENCE_THRESHOLD) -> None:
        self._level_threshold = level_threshold
        self._lock = threading.Lock()
        self._session_start_ts: float | None = None
        self._last_loud_ts: float | None = None
        self._first_loud_ts: float | None = None

    def reset(self) -> None:
        """Mark the start of a new session. Clears all loud-sample timestamps."""
        now = time.monotonic()
        with self._lock:
            self._session_start_ts = now
            self._last_loud_ts = None
            self._first_loud_ts = None

    def update(self, level: float) -> None:
        """Feed an audio level (0..1, normalised RMS). Called on audio thread."""
        if level < self._level_threshold:
            return
        now = time.monotonic()
        with self._lock:
            self._last_loud_ts = now
            if self._first_loud_ts is None:
                self._first_loud_ts = now

    def speech_detected(self) -> bool:
        """True once any sample crossed the threshold this session."""
        with self._lock:
            return self._first_loud_ts is not None

    def silence_duration(self) -> float:
        """Seconds since the most recent loud sample, OR since session start
        if no loud sample has been observed yet.

        Floor at session_start so callers comparing against a timeout
        (e.g. STREAM_AUTO_STOP_SECONDS) get a sane "0 at session start,
        grows linearly" behaviour even when the user hasn't spoken yet.
        Returning inf would instantly trip every threshold.
        """
        with self._lock:
            last = self._last_loud_ts
            start = self._session_start_ts
        # Use the LATER of (last loud sample, session start) as our
        # reference point, so silence is always measured from the most
        # recent meaningful event in the session.
        ref = max(filter(None, (last, start)), default=None)
        if ref is None:
            return 0.0
        return time.monotonic() - ref

    def elapsed_since_start(self) -> float:
        """Seconds since the session was reset (started). 0.0 if not started."""
        with self._lock:
            start = self._session_start_ts
        if start is None:
            return 0.0
        return time.monotonic() - start

    def silence_since_speech_started(self) -> float:
        """Seconds of silence accumulated since FIRST loud sample.

        Returns 0.0 if speech has not yet been detected — caller should pair
        this with ``speech_detected()`` for the "fire after silence post-speech"
        decision.
        """
        with self._lock:
            last = self._last_loud_ts
            first = self._first_loud_ts
        if first is None or last is None:
            return 0.0
        return time.monotonic() - last
