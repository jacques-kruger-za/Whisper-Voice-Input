"""Audio capture and processing module."""

from .recorder import AudioRecorder
from .processor import validate_audio, get_audio_duration, normalize_audio
from .silence_monitor import SilenceMonitor

__all__ = [
    "AudioRecorder",
    "validate_audio",
    "get_audio_duration",
    "normalize_audio",
    "SilenceMonitor",
]
