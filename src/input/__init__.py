"""Input handling module (hotkeys and text injection)."""

from .hotkey import HotkeyManager, HotkeyCapture, hotkey_to_string
from .injector import TextInjector, get_injector, inject_text
from .window_focus import (
    save_foreground_window, restore_foreground_window,
    is_window_valid, get_foreground_window_if_external,
)

__all__ = [
    "HotkeyManager",
    "HotkeyCapture",
    "hotkey_to_string",
    "TextInjector",
    "get_injector",
    "inject_text",
    "save_foreground_window",
    "restore_foreground_window",
    "is_window_valid",
    "get_foreground_window_if_external",
]
