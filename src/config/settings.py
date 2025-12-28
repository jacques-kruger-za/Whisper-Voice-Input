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


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
