"""Text injection using clipboard and keyboard simulation."""

import time
import pyperclip
import pyautogui


class TextInjector:
    """Inject text into focused application using clipboard paste."""

    def __init__(self):
        # Small delays for reliability
        self._pre_paste_delay = 0.05  # Delay before paste
        self._post_paste_delay = 0.1  # Delay after paste

        # Configure pyautogui
        pyautogui.PAUSE = 0.02
        pyautogui.FAILSAFE = False  # Don't stop on corner

    def inject(self, text: str) -> bool:
        """
        Inject text into the currently focused text field.

        Uses clipboard + Ctrl+V for fast and reliable injection.

        Args:
            text: Text to inject

        Returns:
            True if injection was attempted, False on error
        """
        if not text:
            return False

        try:
            # Save current clipboard content
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                old_clipboard = None

            # Copy text to clipboard
            pyperclip.copy(text)

            # Small delay to ensure clipboard is ready
            time.sleep(self._pre_paste_delay)

            # Simulate Ctrl+V
            pyautogui.hotkey("ctrl", "v")

            # Wait for paste to complete
            time.sleep(self._post_paste_delay)

            # Optionally restore old clipboard (commented out as it can cause issues)
            # if old_clipboard is not None:
            #     time.sleep(0.1)
            #     pyperclip.copy(old_clipboard)

            return True

        except Exception as e:
            print(f"Text injection error: {e}")
            return False

    def inject_with_keystroke(self, text: str) -> bool:
        """
        Alternative: Inject text using keystroke simulation.

        Slower but doesn't use clipboard. Use for short text or
        when clipboard preservation is critical.

        Args:
            text: Text to inject

        Returns:
            True if injection was attempted
        """
        if not text:
            return False

        try:
            # Type each character
            # Note: pyautogui.write() doesn't handle special chars well
            for char in text:
                if char == "\n":
                    pyautogui.press("enter")
                elif char == "\t":
                    pyautogui.press("tab")
                else:
                    pyautogui.write(char, interval=0.01)

            return True

        except Exception as e:
            print(f"Keystroke injection error: {e}")
            return False


# Global injector instance
_injector: TextInjector | None = None


def get_injector() -> TextInjector:
    """Get the global text injector instance."""
    global _injector
    if _injector is None:
        _injector = TextInjector()
    return _injector


def inject_text(text: str) -> bool:
    """Convenience function to inject text."""
    return get_injector().inject(text)
