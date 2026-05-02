"""Settings management with JSON persistence."""

import json
from pathlib import Path
from typing import Any
from platformdirs import user_config_dir

from .constants import (
    APP_NAME,
    APP_AUTHOR,
    DEFAULT_HOTKEY,
    DEFAULT_MODEL,
    DEFAULT_LANGUAGE,
    DEFAULT_ENGINE,
    ENGINE_LOCAL,
    DEFAULT_WIDGET_SIZE,
)


class Settings:
    """Manage application settings with JSON persistence."""

    def __init__(self):
        self._config_dir = Path(user_config_dir(APP_NAME, APP_AUTHOR))
        self._config_file = self._config_dir / "settings.json"
        self._settings: dict[str, Any] = {}
        self._load()

    def _get_defaults(self) -> dict[str, Any]:
        """Return default settings."""
        return {
            "hotkey": DEFAULT_HOTKEY.copy(),
            "audio_device": None,  # None = system default
            "engine": DEFAULT_ENGINE,
            "model": DEFAULT_MODEL,
            "language": DEFAULT_LANGUAGE,
            "openai_api_key": "",
            "start_with_windows": False,
            "show_widget": True,
            "widget_position": None,  # None = top-right
            "widget_size": DEFAULT_WIDGET_SIZE,
            "first_run": True,
            "custom_vocabulary": [],
            "command_threshold": 80,
            "commands_enabled": True,
            "custom_punctuation": {},
            "custom_commands": {},
            "streaming_mode": False,
        }

    def _load(self) -> None:
        """Load settings from file or create defaults."""
        self._settings = self._get_defaults()

        if self._config_file.exists():
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._settings.update(saved)
            except (json.JSONDecodeError, IOError):
                pass  # Use defaults on error

    def save(self) -> None:
        """Save current settings to file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with open(self._config_file, "w", encoding="utf-8") as f:
            json.dump(self._settings, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value and save."""
        self._settings[key] = value
        self.save()

    @property
    def hotkey(self) -> dict:
        """Get hotkey configuration."""
        return self._settings.get("hotkey", DEFAULT_HOTKEY.copy())

    @hotkey.setter
    def hotkey(self, value: dict) -> None:
        self.set("hotkey", value)

    @property
    def audio_device(self) -> str | None:
        """Get selected audio device."""
        return self._settings.get("audio_device")

    @audio_device.setter
    def audio_device(self, value: str | None) -> None:
        self.set("audio_device", value)

    @property
    def engine(self) -> str:
        """Get recognition engine (local or api)."""
        return self._settings.get("engine", ENGINE_LOCAL)

    @engine.setter
    def engine(self, value: str) -> None:
        self.set("engine", value)

    @property
    def model(self) -> str:
        """Get Whisper model name."""
        return self._settings.get("model", DEFAULT_MODEL)

    @model.setter
    def model(self, value: str) -> None:
        self.set("model", value)

    @property
    def language(self) -> str:
        """Get transcription language."""
        return self._settings.get("language", DEFAULT_LANGUAGE)

    @language.setter
    def language(self, value: str) -> None:
        self.set("language", value)

    @property
    def openai_api_key(self) -> str:
        """Get OpenAI API key."""
        return self._settings.get("openai_api_key", "")

    @openai_api_key.setter
    def openai_api_key(self, value: str) -> None:
        self.set("openai_api_key", value)

    @property
    def start_with_windows(self) -> bool:
        """Get start with Windows setting."""
        return self._settings.get("start_with_windows", False)

    @start_with_windows.setter
    def start_with_windows(self, value: bool) -> None:
        self.set("start_with_windows", value)

    @property
    def show_widget(self) -> bool:
        """Get widget visibility setting."""
        return self._settings.get("show_widget", True)

    @show_widget.setter
    def show_widget(self, value: bool) -> None:
        self.set("show_widget", value)

    @property
    def widget_position(self) -> tuple[int, int] | None:
        """Get saved widget position."""
        pos = self._settings.get("widget_position")
        if pos and isinstance(pos, list) and len(pos) == 2:
            return tuple(pos)
        return None

    @widget_position.setter
    def widget_position(self, value: tuple[int, int] | None) -> None:
        self.set("widget_position", list(value) if value else None)

    @property
    def widget_size(self) -> str:
        """Get widget size (compact, medium, large)."""
        return self._settings.get("widget_size", DEFAULT_WIDGET_SIZE)

    @widget_size.setter
    def widget_size(self, value: str) -> None:
        self.set("widget_size", value)

    @property
    def first_run(self) -> bool:
        """Check if this is first run."""
        return self._settings.get("first_run", True)

    @first_run.setter
    def first_run(self, value: bool) -> None:
        self.set("first_run", value)

    @property
    def custom_vocabulary(self) -> list[str]:
        """Get custom vocabulary list."""
        vocab = self._settings.get("custom_vocabulary", [])
        return vocab if isinstance(vocab, list) else []

    @custom_vocabulary.setter
    def custom_vocabulary(self, value: list[str]) -> None:
        self.set("custom_vocabulary", value)

    @property
    def command_threshold(self) -> int:
        """Get fuzzy command-matching threshold (70-90)."""
        return int(self._settings.get("command_threshold", 80))

    @command_threshold.setter
    def command_threshold(self, value: int) -> None:
        self.set("command_threshold", int(value))

    @property
    def commands_enabled(self) -> bool:
        """Whether voice commands fire (master toggle for the wake-word path)."""
        return bool(self._settings.get("commands_enabled", True))

    @commands_enabled.setter
    def commands_enabled(self, value: bool) -> None:
        self.set("commands_enabled", bool(value))

    @property
    def custom_punctuation(self) -> dict[str, str]:
        """User-added spoken-punctuation mappings (phrase -> symbol)."""
        v = self._settings.get("custom_punctuation", {})
        return v if isinstance(v, dict) else {}

    @custom_punctuation.setter
    def custom_punctuation(self, value: dict[str, str]) -> None:
        self.set("custom_punctuation", dict(value))

    @property
    def custom_commands(self) -> dict[str, str]:
        """User-added editor commands (phrase -> keystroke)."""
        v = self._settings.get("custom_commands", {})
        return v if isinstance(v, dict) else {}

    @custom_commands.setter
    def custom_commands(self, value: dict[str, str]) -> None:
        self.set("custom_commands", dict(value))

    @property
    def streaming_mode(self) -> bool:
        """Real-time streaming transcription (vs record-then-batch)."""
        return bool(self._settings.get("streaming_mode", False))

    @streaming_mode.setter
    def streaming_mode(self, value: bool) -> None:
        self.set("streaming_mode", bool(value))


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
