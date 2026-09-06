"""A preview round that was in flight when finalize()/stop() ran must be
discarded, and the rolling window must start empty after a commit.
Run: venv/Scripts/python -m pytest tests/test_stream_preview_gate.py
"""
import threading

import numpy as np

from src.recognition.stream import StreamingTranscriber


class _Seg:
    def __init__(self, text):
        self.text = text


class _BlockingRecognizer:
    """transcribe_array blocks until released; lets the test finalize mid-round."""

    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def transcribe_array(self, samples, **_):
        if threading.current_thread().name != "StreamingTranscriber":
            return [_Seg("final text")]  # finalize() on the caller's thread
        self.started.set()
        self.release.wait(timeout=5)
        return [_Seg("stale text")]


def _make(recognizer, previews):
    st = StreamingTranscriber(
        recognizer, sample_rate=100, window_seconds=2.0, interval_seconds=0.01,
        on_preview=previews.append,
    )
    st.start()
    st.feed(np.zeros(200, dtype=np.float32))  # > _MIN_BUFFER_SECONDS at 100 Hz
    assert recognizer.started.wait(timeout=5), "round never started"
    return st


def test_finalize_mid_round_discards_preview():
    rec, previews = _BlockingRecognizer(), []
    st = _make(rec, previews)
    rec.started.clear()
    st.finalize()                      # bumps generation, empties window
    rec.release.set()                  # let the stale round complete
    # Window was cleared, so no new round can start until fresh audio arrives.
    assert not rec.started.wait(timeout=0.2)
    st.stop()
    assert previews == []


def test_stop_mid_round_discards_preview():
    rec, previews = _BlockingRecognizer(), []
    st = _make(rec, previews)
    st.stop()
    rec.release.set()
    st._worker = None
    threading.Event().wait(0.1)
    assert previews == []


if __name__ == "__main__":
    test_finalize_mid_round_discards_preview()
    test_stop_mid_round_discards_preview()
    print("ok")
