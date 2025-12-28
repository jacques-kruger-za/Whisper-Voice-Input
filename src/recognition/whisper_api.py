"""OpenAI Whisper API speech recognition."""

from pathlib import Path

from .base import BaseRecognizer, RecognitionResult


class APIWhisperRecognizer(BaseRecognizer):
    """Speech recognition using OpenAI Whisper API."""

    def __init__(self, api_key: str = ""):
        self._api_key = api_key
        self._client = None

    def set_api_key(self, api_key: str) -> None:
        """Set or update the API key."""
        self._api_key = api_key
        self._client = None  # Force re-init

    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None and self._api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except Exception:
                pass
        return self._client

    def transcribe(self, audio_path: Path, language: str | None = None) -> RecognitionResult:
        """Transcribe audio file using OpenAI Whisper API."""
        if not self._api_key:
            return RecognitionResult(
                text="",
                error="OpenAI API key not configured. Please add your API key in settings.",
            )

        client = self._get_client()
        if not client:
            return RecognitionResult(
                text="",
                error="Failed to initialize OpenAI client.",
            )

        try:
            # Map language codes
            lang = None
            if language and language != "en":
                lang = language.split("-")[0] if "-" in language else language

            with open(audio_path, "rb") as audio_file:
                kwargs = {
                    "model": "whisper-1",
                    "file": audio_file,
                    "response_format": "text",
                }
                if lang:
                    kwargs["language"] = lang

                transcript = client.audio.transcriptions.create(**kwargs)

            # API returns string directly with response_format="text"
            text = transcript if isinstance(transcript, str) else str(transcript)

            return RecognitionResult(
                text=text.strip(),
                language=lang or "en",
            )

        except Exception as e:
            error_msg = str(e)
            if "invalid_api_key" in error_msg.lower():
                error_msg = "Invalid OpenAI API key. Please check your settings."
            elif "quota" in error_msg.lower():
                error_msg = "OpenAI API quota exceeded. Please check your usage."
            return RecognitionResult(text="", error=error_msg)

    def is_available(self) -> bool:
        """Check if OpenAI API is available (key configured)."""
        return bool(self._api_key)

    def get_name(self) -> str:
        """Get display name."""
        return "OpenAI Whisper API"
