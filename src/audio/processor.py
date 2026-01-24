"""Audio preprocessing utilities."""

from pathlib import Path

import numpy as np
from scipy.io import wavfile

from ..config.constants import SAMPLE_RATE
from ..config.logging_config import get_logger

logger = get_logger(__name__)


def validate_audio(audio_path: Path) -> bool:
    """Check if audio file is valid and has content."""
    try:
        sample_rate, audio = wavfile.read(audio_path)
        # Check minimum length (at least 0.5 seconds)
        min_samples = int(SAMPLE_RATE * 0.5)
        if len(audio) < min_samples:
            return False
        # Check if audio has actual content (not silence)
        if np.abs(audio).mean() < 10:  # Very low average amplitude
            return False
        return True
    except Exception as e:
        logger.warning("Failed to validate audio file %s: %s", audio_path, e)
        return False


def get_audio_duration(audio_path: Path) -> float:
    """Get duration of audio file in seconds."""
    try:
        sample_rate, audio = wavfile.read(audio_path)
        return len(audio) / sample_rate
    except Exception as e:
        logger.warning("Failed to get audio duration for %s: %s", audio_path, e)
        return 0.0


def normalize_audio(audio_path: Path) -> Path:
    """Normalize audio levels. Returns same path (modifies in place)."""
    try:
        sample_rate, audio = wavfile.read(audio_path)

        # Convert to float for processing
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32767.0

        # Find peak and normalize
        peak = np.abs(audio).max()
        if peak > 0 and peak < 0.8:
            audio = audio * (0.9 / peak)
            audio = np.clip(audio, -1.0, 1.0)

        # Convert back to int16
        audio_int16 = (audio * 32767).astype(np.int16)
        wavfile.write(audio_path, sample_rate, audio_int16)

    except Exception as e:
        logger.warning("Failed to normalize audio %s, returning original: %s", audio_path, e)

    return audio_path
