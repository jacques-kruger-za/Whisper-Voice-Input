"""Base class for speech recognition engines."""

from abc import ABC, abstractmethod
from pathlib import Path


class RecognitionResult:
    """Result from speech recognition."""

    def __init__(
        self,
        text: str,
        language: str | None = None,
        confidence: float | None = None,
        error: str | None = None,
    ):
        self.text = text
        self.language = language
        self.confidence = confidence
        self.error = error
        self.success = error is None and bool(text.strip())

    def __repr__(self) -> str:
        if self.error:
            return f"RecognitionResult(error={self.error!r})"
        return f"RecognitionResult(text={self.text!r}, lang={self.language})"


class BaseRecognizer(ABC):
    """Abstract base class for speech recognizers."""

    @abstractmethod
    def transcribe(self, audio_path: Path, language: str | None = None) -> RecognitionResult:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to WAV audio file
            language: Language code (e.g., 'en', 'en-US') or None for auto-detect

        Returns:
            RecognitionResult with transcribed text or error
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this recognizer is available and ready to use."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get display name of this recognizer."""
        pass
