"""Speech recognition module."""

from .base import BaseRecognizer, RecognitionResult
from .whisper_local import LocalWhisperRecognizer
from .whisper_api import APIWhisperRecognizer
from .cleanup import cleanup_text, add_punctuation
from .commands import CommandResult, classify_transcription
from .command_processor import CommandProcessor

__all__ = [
    "BaseRecognizer",
    "RecognitionResult",
    "LocalWhisperRecognizer",
    "APIWhisperRecognizer",
    "cleanup_text",
    "add_punctuation",
    "CommandResult",
    "classify_transcription",
    "CommandProcessor",
]
