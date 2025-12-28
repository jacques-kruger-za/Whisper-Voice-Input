"""Input handling module (hotkeys and text injection)."""

from .hotkey import HotkeyManager, HotkeyCapture, hotkey_to_string
from .injector import TextInjector, get_injector, inject_text

__all__ = [
    "HotkeyManager",
    "HotkeyCapture",
    "hotkey_to_string",
    "TextInjector",
    "get_injector",
    "inject_text",
]
