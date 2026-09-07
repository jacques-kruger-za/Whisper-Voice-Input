"""Session record + recovery, and clipboard preservation.
Run: venv/Scripts/python tests/test_recovery.py
"""
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.recognition.history import DictationHistory  # noqa: E402
from src.input import injector as inj  # noqa: E402


def test_history_records_whole_session_and_persists():
    d = Path(tempfile.mkdtemp())
    h = DictationHistory(d)
    assert h.last_text is None
    h.begin()
    h.append("first sentence.")
    assert h.last_text == "first sentence."            # mid-session = so far
    h.append("second sentence.")
    assert h.end() == "first sentence. second sentence."
    h.begin()
    assert h.end() is None                             # empty session not stored
    assert h.last_text == "first sentence. second sentence."

    h2 = DictationHistory(d)                           # reloads from disk
    assert h2.last_text == "first sentence. second sentence."
    assert len(h2.recent()) == 1

    h3 = DictationHistory(d, max_sessions=2)
    for i in range(4):
        h3.begin(); h3.append(f"s{i}"); h3.end()
    assert [t for _, t in h3.recent()] == ["s3", "s2"]  # capped, newest first


def test_clipboard_restore_keeps_original_across_streaming_chunks():
    """Chunks arrive faster than the restore delay: the pending restore is
    cancelled each time and the ORIGINAL clipboard comes back at the end."""
    clip = {"v": "user's own text"}
    pressed = []
    inj.pyperclip.paste = lambda: clip["v"]
    inj.pyperclip.copy = lambda t: clip.__setitem__("v", t)
    inj.pyautogui.hotkey = lambda *a: pressed.append(a)
    inj.CLIPBOARD_RESTORE_DELAY_S = 0.15

    t = inj.TextInjector()
    t._pre_paste_delay = t._post_paste_delay = 0.0
    t.inject("chunk one", restore_clipboard=True)
    assert clip["v"] == "chunk one" and pressed == [("ctrl", "v")]
    time.sleep(0.05)
    t.inject("chunk two", restore_clipboard=True)      # before restore fires
    assert clip["v"] == "chunk two"
    time.sleep(0.3)
    assert clip["v"] == "user's own text"              # original, not "chunk one"

    # Non-text / empty clipboard is never overwritten with ""
    clip["v"] = ""
    t.inject("chunk three", restore_clipboard=True)
    time.sleep(0.3)
    assert clip["v"] == "chunk three"

    # Preservation off: nothing scheduled
    clip["v"] = "keep"
    t.inject("chunk four", restore_clipboard=False)
    time.sleep(0.3)
    assert clip["v"] == "chunk four"


if __name__ == "__main__":
    test_history_records_whole_session_and_persists()
    test_clipboard_restore_keeps_original_across_streaming_chunks()
    print("ok")
