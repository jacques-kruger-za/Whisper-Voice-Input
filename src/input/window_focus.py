"""Win32 window focus save/restore using ctypes.

Beyond the top-level window we remember which CONTROL had keyboard focus
in it (GetGUIThreadInfo) whenever a foreground window is observed, and
restore that control explicitly after activation — not every app puts
focus back on its own. Explorer's shell windows (taskbar, tray overflow,
Start) are never treated as a paste target: clicking our tray icon makes
the taskbar foreground for a moment and the tracker must not remember it.
"""

import os
import time
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
_user32.SetFocus.argtypes = [ctypes.wintypes.HWND]
_user32.SetFocus.restype = ctypes.wintypes.HWND
_user32.GetClassNameW.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.LPWSTR, ctypes.c_int]
_user32.GetClassNameW.restype = ctypes.c_int
_kernel32.GetCurrentThreadId.restype = ctypes.wintypes.DWORD

SW_SHOW = 5

# Explorer / shell windows that can be foreground for a moment around a
# tray or Start click but are never somewhere to paste.
SHELL_WINDOW_CLASSES = frozenset({
    "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "TrayNotifyWnd",
    "NotifyIconOverflowWindow", "Progman", "WorkerW",
    "Windows.UI.Core.CoreWindow", "Xaml_WindowedPopupClass", "#32768",
})


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD), ("flags", ctypes.wintypes.DWORD),
        ("hwndActive", ctypes.wintypes.HWND), ("hwndFocus", ctypes.wintypes.HWND),
        ("hwndCapture", ctypes.wintypes.HWND), ("hwndMenuOwner", ctypes.wintypes.HWND),
        ("hwndMoveSize", ctypes.wintypes.HWND), ("hwndCaret", ctypes.wintypes.HWND),
        ("rcCaret", ctypes.wintypes.RECT),
    ]


_user32.GetGUIThreadInfo.argtypes = [ctypes.wintypes.DWORD, ctypes.POINTER(GUITHREADINFO)]
_user32.GetGUIThreadInfo.restype = ctypes.wintypes.BOOL

# hwnd → control that had keyboard focus the last time we saw hwnd foreground.
_focus_by_window: dict[int, int] = {}
_FOCUS_CACHE_MAX = 32


def get_window_class(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    _user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def is_shell_window(hwnd: int) -> bool:
    return get_window_class(hwnd) in SHELL_WINDOW_CLASSES


def remember_focused_control(hwnd: int) -> int | None:
    """Record which control inside hwnd currently has keyboard focus."""
    thread = _user32.GetWindowThreadProcessId(hwnd, None)
    info = GUITHREADINFO()
    info.cbSize = ctypes.sizeof(GUITHREADINFO)
    if not _user32.GetGUIThreadInfo(thread, ctypes.byref(info)) or not info.hwndFocus:
        return None
    focus = int(info.hwndFocus)
    _focus_by_window[int(hwnd)] = focus
    if len(_focus_by_window) > _FOCUS_CACHE_MAX:
        del _focus_by_window[next(iter(_focus_by_window))]
    return focus


def get_foreground_window_if_external() -> int | None:
    """Foreground window if it is a plausible paste target: another
    process, and not an Explorer shell window. Also remembers which
    control inside it has focus, for restore_foreground_window().
    """
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = ctypes.wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == os.getpid() or is_shell_window(hwnd):
        return None
    remember_focused_control(hwnd)
    return hwnd


def save_foreground_window() -> int | None:
    """Capture the current foreground window handle.

    Must be called BEFORE our app takes focus (e.g., in the hotkey thread
    or before processing a tray/widget click).
    """
    hwnd = _user32.GetForegroundWindow()
    if hwnd:
        remember_focused_control(hwnd)
        logger.debug("Saved foreground window: HWND=%s title='%s'", hwnd, get_window_title(hwnd))
        return hwnd
    logger.debug("No foreground window to save")
    return None


def restore_foreground_window(hwnd: int) -> bool:
    """Restore focus to a previously saved window, and to the control
    inside it that had focus when we last saw it. Verifies the window is
    actually foreground afterwards; one retry. Returns False if not — the
    caller must then NOT paste blind.

    Uses the AttachThreadInput trick so a background process may call
    SetForegroundWindow / SetFocus on another thread's windows.
    """
    if not hwnd:
        logger.info("No HWND to restore")
        return False
    if not is_window_valid(hwnd):
        logger.warning("Cannot restore focus: window no longer exists (HWND=%s)", hwnd)
        return False

    focus = _focus_by_window.get(int(hwnd))
    if focus and not is_window_valid(focus):
        focus = None
    logger.info("Restoring focus to HWND=%s title='%s' control=%s", hwnd, get_window_title(hwnd), focus)

    our_thread = _kernel32.GetCurrentThreadId()
    target_thread = _user32.GetWindowThreadProcessId(hwnd, None)

    for attempt in (1, 2):
        attached = False
        try:
            if our_thread != target_thread:
                attached = bool(_user32.AttachThreadInput(our_thread, target_thread, True))
            _user32.ShowWindow(hwnd, SW_SHOW)
            _user32.BringWindowToTop(hwnd)
            _user32.SetForegroundWindow(hwnd)
            if focus:
                _user32.SetFocus(focus)
        finally:
            if attached:
                _user32.AttachThreadInput(our_thread, target_thread, False)

        time.sleep(0.03)
        if _user32.GetForegroundWindow() == hwnd:
            logger.info("Focus restored to HWND=%s (attempt %d)", hwnd, attempt)
            return True
        logger.warning("Foreground is not HWND=%s after attempt %d", hwnd, attempt)
        time.sleep(0.1)
    return False


# ── Event-driven foreground tracking (replaces a 250 ms poll) ─────────────
#
# SetWinEventHook with WINEVENT_OUTOFCONTEXT: Windows calls us on the
# installing thread's message loop only when the foreground window or the
# focused control changes. Zero cost while nothing changes. Must be
# installed from a thread that pumps messages (Qt's main thread does).

EVENT_SYSTEM_FOREGROUND = 0x0003
EVENT_OBJECT_FOCUS = 0x8005
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002
GA_ROOT = 2

_WINEVENTPROC = ctypes.WINFUNCTYPE(
    None, ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD, ctypes.wintypes.HWND,
    ctypes.wintypes.LONG, ctypes.wintypes.LONG, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD,
)
_user32.SetWinEventHook.argtypes = [
    ctypes.wintypes.DWORD, ctypes.wintypes.DWORD, ctypes.wintypes.HMODULE, _WINEVENTPROC,
    ctypes.wintypes.DWORD, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD,
]
_user32.SetWinEventHook.restype = ctypes.wintypes.HANDLE
_user32.UnhookWinEvent.argtypes = [ctypes.wintypes.HANDLE]
_user32.UnhookWinEvent.restype = ctypes.wintypes.BOOL
_user32.GetAncestor.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.UINT]
_user32.GetAncestor.restype = ctypes.wintypes.HWND

_hooks: list = []          # hook handles
_hook_proc = None          # keep the callback alive for the hook's lifetime


def start_foreground_hook(on_external_foreground) -> bool:
    """Call on_external_foreground(top_level_hwnd) whenever another
    process's window becomes foreground or a control in it gains focus.
    Shell windows are ignored. Runs on the installing thread."""
    global _hook_proc
    if _hooks:
        return True

    def _proc(hook, event, hwnd, id_object, id_child, thread, ms):
        try:
            if not hwnd:
                return
            root = _user32.GetAncestor(hwnd, GA_ROOT) or hwnd
            pid = ctypes.wintypes.DWORD()
            _user32.GetWindowThreadProcessId(root, ctypes.byref(pid))
            if pid.value == os.getpid() or is_shell_window(root):
                return
            if event == EVENT_OBJECT_FOCUS:
                _focus_by_window[int(root)] = int(hwnd)
                if len(_focus_by_window) > _FOCUS_CACHE_MAX:
                    del _focus_by_window[next(iter(_focus_by_window))]
            else:
                remember_focused_control(root)
            on_external_foreground(int(root))
        except Exception as e:  # never let an exception escape into Win32
            logger.debug("Foreground hook error: %s", e)

    _hook_proc = _WINEVENTPROC(_proc)
    flags = WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS
    for ev in (EVENT_SYSTEM_FOREGROUND, EVENT_OBJECT_FOCUS):
        h = _user32.SetWinEventHook(ev, ev, None, _hook_proc, 0, 0, flags)
        if h:
            _hooks.append(h)
    ok = len(_hooks) == 2
    logger.info("Foreground hook %s", "installed" if ok else "FAILED")
    return ok


def stop_foreground_hook() -> None:
    global _hook_proc
    for h in _hooks:
        _user32.UnhookWinEvent(h)
    _hooks.clear()
    _hook_proc = None


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
