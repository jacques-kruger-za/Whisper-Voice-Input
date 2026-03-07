"""Win32 window focus save/restore using ctypes."""

import os
import ctypes
import ctypes.wintypes

from ..config.logging_config import get_logger

logger = get_logger(__name__)

# Win32 API bindings
_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

_user32.GetForegroundWindow.restype = ctypes.wintypes.HWND
_user32.SetForegroundWindow.argtypes = [ctypes.wintypes.HWND]
_user32.SetForegroundWindow.restype = ctypes.wintypes.BOOL
_user32.IsWindow.argtypes = [ctypes.wintypes.HWND]
_user32.IsWindow.restype = ctypes.wintypes.BOOL
_user32.GetWindowTextW.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.LPWSTR, ctypes.c_int]
_user32.GetWindowTextW.restype = ctypes.c_int
_user32.GetWindowTextLengthW.argtypes = [ctypes.wintypes.HWND]
_user32.GetWindowTextLengthW.restype = ctypes.c_int
_user32.GetWindowThreadProcessId.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.DWORD)]
_user32.GetWindowThreadProcessId.restype = ctypes.wintypes.DWORD
_user32.AttachThreadInput.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.DWORD, ctypes.wintypes.BOOL]
_user32.AttachThreadInput.restype = ctypes.wintypes.BOOL
_user32.BringWindowToTop.argtypes = [ctypes.wintypes.HWND]
_user32.BringWindowToTop.restype = ctypes.wintypes.BOOL
_user32.ShowWindow.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
_user32.ShowWindow.restype = ctypes.wintypes.BOOL
_kernel32.GetCurrentThreadId.restype = ctypes.wintypes.DWORD

SW_SHOW = 5


def get_foreground_window_if_external() -> int | None:
    """Get the foreground window handle, but only if it belongs to another process.

    Used by the focus tracker timer to silently poll without log spam.
    Returns None if the foreground window is our own (widget, callout, etc.).
    """
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = ctypes.wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == os.getpid():
        return None
    return hwnd


def save_foreground_window() -> int | None:
    """Capture the current foreground window handle.

    Must be called BEFORE our app takes focus (e.g., in the hotkey thread
    or before processing a tray/widget click).

    Returns:
        Window handle (HWND) or None if no foreground window.
    """
    hwnd = _user32.GetForegroundWindow()
    if hwnd:
        title = get_window_title(hwnd)
        logger.debug("Saved foreground window: HWND=%s title='%s'", hwnd, title)
        return hwnd
    logger.debug("No foreground window to save")
    return None


def restore_foreground_window(hwnd: int) -> bool:
    """Restore focus to a previously saved window.

    Uses AttachThreadInput trick to bypass Windows restrictions on
    SetForegroundWindow (a background process normally can't steal focus).

    Args:
        hwnd: Window handle from save_foreground_window().

    Returns:
        True if focus was restored successfully.
    """
    if not hwnd:
        logger.info("No HWND to restore")
        return False

    if not is_window_valid(hwnd):
        title = get_window_title(hwnd)
        logger.warning("Cannot restore focus: window no longer exists (HWND=%s, title='%s')", hwnd, title)
        return False

    title = get_window_title(hwnd)
    logger.info("Restoring focus to HWND=%s title='%s'", hwnd, title)

    # Get thread IDs for our process and the target window
    our_thread = _kernel32.GetCurrentThreadId()
    target_thread = _user32.GetWindowThreadProcessId(hwnd, None)

    attached = False
    try:
        # Attach our thread input to the target window's thread.
        # This lets us call SetForegroundWindow even from a background process.
        if our_thread != target_thread:
            attached = bool(_user32.AttachThreadInput(our_thread, target_thread, True))
            if attached:
                logger.debug("Attached thread input (ours=%s, target=%s)", our_thread, target_thread)

        # Now SetForegroundWindow should succeed
        _user32.ShowWindow(hwnd, SW_SHOW)
        _user32.BringWindowToTop(hwnd)
        result = _user32.SetForegroundWindow(hwnd)

        if result:
            logger.info("Focus restored to HWND=%s", hwnd)
        else:
            logger.warning("SetForegroundWindow returned false for HWND=%s", hwnd)

        return bool(result)
    finally:
        # Detach thread input
        if attached:
            _user32.AttachThreadInput(our_thread, target_thread, False)
            logger.debug("Detached thread input")


def is_window_valid(hwnd: int) -> bool:
    """Check if a window handle is still valid."""
    return bool(_user32.IsWindow(hwnd))


def get_window_title(hwnd: int) -> str:
    """Get the title text of a window."""
    length = _user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value
