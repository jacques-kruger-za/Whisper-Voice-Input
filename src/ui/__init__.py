"""UI components module."""

from .widget import FloatingWidget
from .tray import TrayIcon
from .settings import SettingsWindow
from .styles import WIDGET_STYLE, SETTINGS_STYLE, TRAY_MENU_STYLE

__all__ = [
    "FloatingWidget",
    "TrayIcon",
    "SettingsWindow",
    "WIDGET_STYLE",
    "SETTINGS_STYLE",
    "TRAY_MENU_STYLE",
]
