"""Global hotkey handling using pynput."""

import threading
from typing import Callable

from pynput import keyboard
from pynput.keyboard import Key, KeyCode


class HotkeyManager:
    """Manage global hotkeys."""

    def __init__(self):
        self._listener: keyboard.Listener | None = None
        self._callback: Callable[[], None] | None = None
        self._hotkey: dict = {}
        self._pressed_keys: set = set()
        self._lock = threading.Lock()

    def _normalize_key(self, key) -> str:
        """Normalize key to string representation."""
        if isinstance(key, Key):
            return key.name.lower()
        elif isinstance(key, KeyCode):
            if key.char:
                return key.char.lower()
            elif key.vk:
                # Handle special keys by virtual key code
                return f"vk_{key.vk}"
        return str(key).lower()

    def _check_hotkey(self) -> bool:
        """Check if current pressed keys match the hotkey."""
        if not self._hotkey:
            return False

        required = set()

        if self._hotkey.get("ctrl"):
            required.add("ctrl_l")
            required.add("ctrl_r")
        if self._hotkey.get("shift"):
            required.add("shift_l")
            required.add("shift_r")
            required.add("shift")
        if self._hotkey.get("alt"):
            required.add("alt_l")
            required.add("alt_r")
            required.add("alt")

        key_name = self._hotkey.get("key", "").lower()
        if key_name:
            required.add(key_name)

        # Check modifiers
        has_ctrl = self._hotkey.get("ctrl", False)
        has_shift = self._hotkey.get("shift", False)
        has_alt = self._hotkey.get("alt", False)

        ctrl_pressed = "ctrl_l" in self._pressed_keys or "ctrl_r" in self._pressed_keys
        shift_pressed = any(k in self._pressed_keys for k in ["shift_l", "shift_r", "shift"])
        alt_pressed = any(k in self._pressed_keys for k in ["alt_l", "alt_r", "alt"])

        if has_ctrl != ctrl_pressed:
            return False
        if has_shift != shift_pressed:
            return False
        if has_alt != alt_pressed:
            return False

        # Check main key
        if key_name and key_name not in self._pressed_keys:
            return False

        return True

    def _on_press(self, key) -> None:
        """Handle key press."""
        with self._lock:
            normalized = self._normalize_key(key)
            self._pressed_keys.add(normalized)

            if self._check_hotkey() and self._callback:
                # Call callback in separate thread to avoid blocking
                threading.Thread(target=self._callback, daemon=True).start()

    def _on_release(self, key) -> None:
        """Handle key release."""
        with self._lock:
            normalized = self._normalize_key(key)
            self._pressed_keys.discard(normalized)

    def set_hotkey(self, hotkey: dict) -> None:
        """
        Set the hotkey configuration.

        Args:
            hotkey: Dict with keys 'ctrl', 'shift', 'alt' (bool) and 'key' (str)
        """
        with self._lock:
            self._hotkey = hotkey.copy()

    def set_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback function for when hotkey is pressed."""
        self._callback = callback

    def start(self) -> None:
        """Start listening for hotkeys."""
        if self._listener is not None:
            return

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        if self._listener:
            self._listener.stop()
            self._listener = None
        with self._lock:
            self._pressed_keys.clear()

    def is_running(self) -> bool:
        """Check if hotkey listener is running."""
        return self._listener is not None and self._listener.is_alive()


class HotkeyCapture:
    """Capture a new hotkey combination from user input."""

    def __init__(self):
        self._listener: keyboard.Listener | None = None
        self._result: dict | None = None
        self._callback: Callable[[dict], None] | None = None
        self._pressed: set = set()
        self._main_key: str | None = None

    def _on_press(self, key) -> None:
        """Track pressed keys."""
        if isinstance(key, Key):
            name = key.name.lower()
            if "ctrl" in name:
                self._pressed.add("ctrl")
            elif "shift" in name:
                self._pressed.add("shift")
            elif "alt" in name:
                self._pressed.add("alt")
            else:
                self._main_key = name
        elif isinstance(key, KeyCode):
            if key.char:
                self._main_key = key.char.lower()

    def _on_release(self, key) -> bool:
        """Capture hotkey on release of main key."""
        if self._main_key:
            self._result = {
                "ctrl": "ctrl" in self._pressed,
                "shift": "shift" in self._pressed,
                "alt": "alt" in self._pressed,
                "key": self._main_key,
            }
            if self._callback:
                self._callback(self._result)
            return False  # Stop listener
        return True

    def capture(self, callback: Callable[[dict], None]) -> None:
        """
        Start capturing a hotkey.

        Args:
            callback: Called with hotkey dict when captured
        """
        self._callback = callback
        self._pressed = set()
        self._main_key = None
        self._result = None

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def cancel(self) -> None:
        """Cancel hotkey capture."""
        if self._listener:
            self._listener.stop()
            self._listener = None


def hotkey_to_string(hotkey: dict) -> str:
    """Convert hotkey dict to display string."""
    parts = []
    if hotkey.get("ctrl"):
        parts.append("Ctrl")
    if hotkey.get("shift"):
        parts.append("Shift")
    if hotkey.get("alt"):
        parts.append("Alt")
    if hotkey.get("key"):
        key = hotkey["key"]
        # Capitalize single letters and special keys
        if len(key) == 1:
            key = key.upper()
        else:
            key = key.capitalize()
        parts.append(key)
    return "+".join(parts) if parts else "Not set"
