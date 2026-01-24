"""Audio recording using sounddevice."""

import tempfile
import threading
from pathlib import Path
from typing import Callable

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

from ..config.constants import SAMPLE_RATE, CHANNELS
from ..config.logging_config import get_logger

logger = get_logger(__name__)


class AudioRecorder:
    """Record audio from microphone."""

    def __init__(self, device: str | None = None):
        self._device = device
        self._recording = False
        self._audio_data: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._level_callback: Callable[[float], None] | None = None

    def set_device(self, device: str | None) -> None:
        """Set the audio input device."""
        logger.debug("Setting audio device to: %s", device)
        self._device = device

    def set_level_callback(self, callback: Callable[[float], None]) -> None:
        """Set callback for audio level updates (0.0 to 1.0)."""
        self._level_callback = callback

    @staticmethod
    def get_devices() -> list[dict]:
        """Get list of available audio input devices."""
        devices = []
        for i, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0:
                devices.append({
                    "id": i,
                    "name": dev["name"],
                    "channels": dev["max_input_channels"],
                    "sample_rate": dev["default_samplerate"],
                })
        return devices

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """Callback for audio stream."""
        if status:
            logger.warning("Audio stream status: %s", status)

        with self._lock:
            if self._recording:
                self._audio_data.append(indata.copy())

                # Calculate audio level for visualization
                if self._level_callback:
                    level = np.abs(indata).mean()
                    # Normalize to 0-1 range (assuming 16-bit audio range)
                    normalized = min(1.0, level * 10)
                    self._level_callback(normalized)

    def start(self) -> None:
        """Start recording audio."""
        logger.debug("Starting audio recording")
        with self._lock:
            if self._recording:
                logger.debug("Already recording, ignoring start request")
                return

            self._audio_data = []
            self._recording = True

        # Find device index if name specified
        device_id = None
        if self._device:
            for dev in self.get_devices():
                if dev["name"] == self._device:
                    device_id = dev["id"]
                    logger.debug("Found device '%s' with id %d", self._device, device_id)
                    break
            if device_id is None:
                logger.warning("Requested device '%s' not found, using default", self._device)

        self._stream = sd.InputStream(
            device=device_id,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=np.float32,
            callback=self._audio_callback,
        )
        self._stream.start()
        logger.info("Audio recording started (device=%s, rate=%d, channels=%d)",
                    device_id or "default", SAMPLE_RATE, CHANNELS)

    def stop(self) -> Path | None:
        """Stop recording and return path to audio file."""
        logger.debug("Stopping audio recording")
        with self._lock:
            if not self._recording:
                logger.debug("Not recording, nothing to stop")
                return None
            self._recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            logger.debug("Audio stream closed")

        with self._lock:
            if not self._audio_data:
                logger.warning("No audio data captured")
                return None

            # Concatenate all audio chunks
            audio = np.concatenate(self._audio_data, axis=0)
            chunk_count = len(self._audio_data)
            self._audio_data = []

        # Save to temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False, prefix="whisper_"
        )
        temp_path = Path(temp_file.name)
        temp_file.close()

        # Convert float32 to int16 for WAV
        audio_int16 = (audio * 32767).astype(np.int16)
        wavfile.write(temp_path, SAMPLE_RATE, audio_int16)

        duration = len(audio) / SAMPLE_RATE
        logger.info("Audio recording stopped: %d chunks, %.2f seconds, saved to %s",
                    chunk_count, duration, temp_path)

        return temp_path

    def is_recording(self) -> bool:
        """Check if currently recording."""
        with self._lock:
            return self._recording

    def cancel(self) -> None:
        """Cancel recording without saving."""
        logger.debug("Cancelling audio recording")
        with self._lock:
            self._recording = False
            self._audio_data = []

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            logger.info("Audio recording cancelled")
