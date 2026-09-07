"""Text injection using clipboard paste, with optional clipboard restore.

The user's clipboard is put back a few seconds after a paste (Superwhisper
does the same), never immediately: some apps read the clipboard late. In
streaming mode chunks arrive every few seconds, so a pending restore is
cancelled by the next inject and the ORIGINAL clipboard is what finally
comes back, not one of our own chunks.

Known limit: pyperclip only sees text. A non-text clipboard (image, files)
reads as empty and is not restored — we never overwrite it with an empty
string either.
"""

import threading
import time

import pyautogui
import pyperclip

from ..config.logging_config import get_logger

logger = get_logger(__name__)

CLIPBOARD_RESTORE_DELAY_S = 3.0


class TextInjector:
    """Inject text into the focused application using clipboard paste."""

    def __init__(self):
        self._pre_paste_delay = 0.05
        self._post_paste_delay = 0.1
        self._lock = threading.Lock()
        self._restore_timer: threading.Timer | None = None
        self._saved_clipboard: str | None = None
        pyautogui.PAUSE = 0.02
        pyautogui.FAILSAFE = False  # Don't stop on corner

    def inject(self, text: str, restore_clipboard: bool = False) -> bool:
        """Paste `text` into the focused field via clipboard + Ctrl+V.

        Returns True if the paste was attempted. There is no way to know
        whether the target accepted it; see target_check for the pre-check.
        """
        if not text:
            return False
        try:
            with self._lock:
                self._cancel_restore_locked()
                if restore_clipboard and self._saved_clipboard is None:
                    try:
                        old = pyperclip.paste()
                    except Exception:
                        old = ""
                    # Empty means "nothing" or "not text" — nothing to restore.
                    self._saved_clipboard = old if old else None

            pyperclip.copy(text)
            time.sleep(self._pre_paste_delay)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(self._post_paste_delay)

            with self._lock:
                if restore_clipboard and self._saved_clipboard is not None:
                    self._restore_timer = threading.Timer(CLIPBOARD_RESTORE_DELAY_S, self._restore)
                    self._restore_timer.daemon = True
                    self._restore_timer.start()
                elif not restore_clipboard:
                    self._saved_clipboard = None
            return True
        except Exception as e:
            logger.error("Text injection error: %s", e)
            return False

    def _cancel_restore_locked(self) -> None:
        if self._restore_timer is not None:
            self._restore_timer.cancel()
            self._restore_timer = None

    def _restore(self) -> None:
        with self._lock:
            saved, self._saved_clipboard = self._saved_clipboard, None
            self._restore_timer = None
        if saved is None:
            return
        try:
            pyperclip.copy(saved)
            logger.debug("Clipboard restored (%d chars)", len(saved))
        except Exception as e:
            logger.warning("Clipboard restore failed: %s", e)

    def inject_with_keystroke(self, text: str) -> bool:
        """Alternative: type the text. Slower, no clipboard involved."""
        if not text:
            return False
        try:
            for char in text:
                if char == "\n":
                    pyautogui.press("enter")
                elif char == "\t":
                    pyautogui.press("tab")
                else:
                    pyautogui.write(char, interval=0.01)
            return True
        except Exception as e:
            logger.error("Keystroke injection error: %s", e)
            return False


# Global injector instance
_injector: TextInjector | None = None


def get_injector() -> TextInjector:
    global _injector
    if _injector is None:
        _injector = TextInjector()
    return _injector


def inject_text(text: str, restore_clipboard: bool = False) -> bool:
    """Convenience function to inject text."""
    return get_injector().inject(text, restore_clipboard=restore_clipboard)
