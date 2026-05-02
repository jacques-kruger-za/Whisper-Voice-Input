"""S1 smoke test: feed a WAV through StreamingTranscriber in real-time chunks.

Usage: venv/Scripts/python -m scripts.smoke_streaming <path-to-wav>

Verifies:
- Worker thread starts
- feed() accepts chunks
- transcribe_array runs each round
- Segments arrive via on_segments callback
- stop() drains cleanly
"""

import sys
import time
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from src.recognition import LocalWhisperRecognizer, StreamingTranscriber


def main(wav_path: Path) -> None:
    rate, data = wavfile.read(str(wav_path))
    if data.ndim > 1:
        data = data.mean(axis=1)
    # Convert int16 -> float32 -1..1
    if data.dtype == np.int16:
        samples = data.astype(np.float32) / 32768.0
    else:
        samples = data.astype(np.float32)

    duration = samples.size / rate
    print(f"Loaded {wav_path.name}: {duration:.2f}s @ {rate}Hz")

    recognizer = LocalWhisperRecognizer("small")
    print("Loading model...")
    if not recognizer._load_model():
        print("Model failed to load")
        return

    rounds_seen = []
    committed_log: list[str] = []
    last_tentative = [""]

    def on_segments(segs):
        rounds_seen.append(segs)
        print(f"  round {len(rounds_seen)}: {len(segs)} segs")

    def on_committed(text):
        committed_log.append(text)
        print(f"    >>> COMMIT: {text!r}")

    def on_tentative(text):
        last_tentative[0] = text
        if text:
            print(f"    ...tent: {text!r}")

    streamer = StreamingTranscriber(
        recognizer,
        sample_rate=rate,
        window_seconds=12.0,
        interval_seconds=1.0,
        language="en",
        on_segments=on_segments,
        on_committed=on_committed,
        on_tentative=on_tentative,
    )

    print("Starting streaming...")
    streamer.start()

    # Feed in 100ms chunks at real-time pace
    chunk_size = rate // 10
    t0 = time.perf_counter()
    for i in range(0, samples.size, chunk_size):
        streamer.feed(samples[i : i + chunk_size])
        time.sleep(0.1)

    print(f"All audio fed in {time.perf_counter() - t0:.2f}s. Waiting 2s for final round...")
    time.sleep(2.0)

    streamer.stop()
    print(f"\nTotal rounds: {len(rounds_seen)}")
    print(f"Committed deltas: {len(committed_log)}")
    print(f"Final committed: {' '.join(committed_log)!r}")
    print(f"Final tentative: {last_tentative[0]!r}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.smoke_streaming <path-to-wav>")
        sys.exit(1)
    main(Path(sys.argv[1]))
