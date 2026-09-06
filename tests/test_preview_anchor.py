"""Streaming preview streams out of the widget: right edge locked just left
of the widget, vertically centred on it, grows leftward with content up to
the width cap, keeps at most VISIBLE + FADE lines, and paints.
Run: QT_QPA_PLATFORM=offscreen venv/Scripts/python tests/test_preview_anchor.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from src.ui.preview import (  # noqa: E402
    PREVIEW_FADE_LINES, PREVIEW_GAP_PX, PREVIEW_PADDING_PX,
    PREVIEW_VISIBLE_LINES, PREVIEW_WIDTH_FRACTION, StreamingPreviewWindow,
)
from src.ui.widget import FloatingWidget  # noqa: E402

app = QApplication.instance() or QApplication([])
SCREEN = app.primaryScreen().availableGeometry()
CAP = int(SCREEN.width() * PREVIEW_WIDTH_FRACTION)


def _centre_y(w):
    return w.y() + w.height() // 2


def test_streams_out_of_widget_and_grows_left():
    widget = FloatingWidget("compact")
    widget.restore_position((0, 400))
    widget.show()
    p = StreamingPreviewWindow()
    p.set_anchor(widget)

    p.set_text("hello")
    short_w = p.width()
    assert p.x() + p.width() == widget.x() - PREVIEW_GAP_PX     # right edge locked to widget
    assert abs(_centre_y(p) - _centre_y(widget)) <= 1            # vertically aligned
    assert short_w < CAP

    p.set_text("hello there this is a longer preview")
    assert p.width() > short_w                                   # grows leftward…
    assert p.x() + p.width() == widget.x() - PREVIEW_GAP_PX      # …right edge stays put

    p.set_text(" ".join(["word"] * 200))
    assert CAP - 60 < p.width() <= CAP                           # capped (last word may not fill), then wraps
    assert len(p._lines) == PREVIEW_VISIBLE_LINES + PREVIEW_FADE_LINES
    assert not p.grab().isNull()

    # Collapsed widget: still attached, now to the thin bar
    widget.set_collapsed(True)
    p.set_text("still attached")
    assert p.x() + p.width() == widget.x() - PREVIEW_GAP_PX

    # Widget disabled: fall back to the bottom-right of the screen
    widget.hide()
    p.set_text("fallback")
    assert p.x() + p.width() < SCREEN.x() + SCREEN.width()
    assert p.y() > SCREEN.y() + SCREEN.height() // 2

    p.set_text("")
    assert not p.isVisible()


if __name__ == "__main__":
    test_streams_out_of_widget_and_grows_left()
    print("ok")
