"""Local speech recognition using Faster-Whisper."""

from pathlib import Path
from typing import TYPE_CHECKING

from .base import BaseRecognizer, RecognitionResult
from ..config.constants import DEFAULT_MODEL
from ..config.logging_config import get_logger

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

logger = get_logger(__name__)


class LocalWhisperRecognizer(BaseRecognizer):
    """Speech recognition using Faster-Whisper (local)."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self._model_name = model_name
        self._model: "WhisperModel | None" = None
        self._loading = False

    def _load_model(self) -> bool:
        """Lazy load the Whisper model."""
        if self._model is not None:
            return True

        if self._loading:
            logger.debug("Model loading already in progress")
            return False

        self._loading = True
        logger.info("Loading Whisper model '%s'...", self._model_name)
        try:
            from faster_whisper import WhisperModel

            # Use CPU by default, GPU if available
            # compute_type: int8 for CPU, float16 for GPU
            self._model = WhisperModel(
                self._model_name,
                device="auto",  # Will use CUDA if available
                compute_type="auto",  # Will pick best for device
            )
            logger.info("Whisper model '%s' loaded successfully", self._model_name)
            return True
        except Exception as e:
            logger.error("Failed to load Whisper model '%s': %s", self._model_name, e)
            return False
        finally:
            self._loading = False

    def set_model(self, model_name: str) -> None:
        """Change the model (will reload on next transcription)."""
        if model_name != self._model_name:
            logger.info("Changing Whisper model from '%s' to '%s'", self._model_name, model_name)
            self._model_name = model_name
            self._model = None

    def transcribe(self, audio_path: Path, language: str | None = None) -> RecognitionResult:
        """Transcribe audio file using Faster-Whisper."""
        logger.debug("Starting transcription of '%s' (language=%s)", audio_path, language)

        if not self._load_model():
            logger.error("Transcription failed: model not available")
            return RecognitionResult(
                text="",
                error="Failed to load Whisper model. Please check your installation.",
            )

        try:
            # Map language codes
            lang = None
            if language and language != "en":
                # Strip region suffix for Whisper (en-US -> en)
                lang = language.split("-")[0] if "-" in language else language

            logger.debug("Calling Whisper transcribe with language=%s", lang)

            # Transcribe
            segments, info = self._model.transcribe(
                str(audio_path),
                language=lang,
                beam_size=5,
                best_of=5,
                temperature=0.0,
                condition_on_previous_text=True,
                vad_filter=True,  # Filter out non-speech
            )

            # Collect text from segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)

            full_text = " ".join(text_parts).strip()

            logger.info("Transcription complete: %d segments, detected_language=%s, confidence=%.2f",
                        len(text_parts), info.language, info.language_probability)
            logger.debug("Transcribed text: %s", full_text[:100] + "..." if len(full_text) > 100 else full_text)

            return RecognitionResult(
                text=full_text,
                language=info.language,
                confidence=info.language_probability,
            )

        except Exception as e:
            logger.error("Transcription error: %s", e)
            return RecognitionResult(text="", error=str(e))

    def is_available(self) -> bool:
        """Check if Faster-Whisper is available."""
        try:
            import faster_whisper  # noqa: F401
            return True
        except ImportError:
            return False

    def get_name(self) -> str:
        """Get display name."""
        return f"Local Whisper ({self._model_name})"

    def unload_model(self) -> None:
        """Unload the model to free memory."""
        if self._model is not None:
            logger.info("Unloading Whisper model '%s'", self._model_name)
        self._model = None
