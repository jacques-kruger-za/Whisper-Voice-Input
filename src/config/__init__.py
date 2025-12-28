"""Configuration module."""

from .settings import Settings, get_settings
from .constants import (
    APP_NAME,
    APP_VERSION,
    STATE_IDLE,
    STATE_RECORDING,
    STATE_PROCESSING,
    STATE_ERROR,
    WHISPER_MODELS,
    SUPPORTED_LANGUAGES,
    ENGINE_LOCAL,
    ENGINE_API,
    WIDGET_SIZES,
    DEFAULT_WIDGET_SIZE,
    COLOR_BACKGROUND,
    COLOR_IDLE,
    COLOR_RECORDING,
    COLOR_PROCESSING,
    COLOR_ERROR,
)

__all__ = [
    "Settings",
    "get_settings",
    "APP_NAME",
    "APP_VERSION",
    "STATE_IDLE",
    "STATE_RECORDING",
    "STATE_PROCESSING",
    "STATE_ERROR",
    "WHISPER_MODELS",
    "SUPPORTED_LANGUAGES",
    "ENGINE_LOCAL",
    "ENGINE_API",
    "WIDGET_SIZES",
    "DEFAULT_WIDGET_SIZE",
    "COLOR_BACKGROUND",
    "COLOR_IDLE",
    "COLOR_RECORDING",
    "COLOR_PROCESSING",
    "COLOR_ERROR",
]
