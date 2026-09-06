"""Dock behaviour of FloatingWidget: pinned to the right screen edge, drag is
vertical only, Hide collapses to a thin bar that expands on hover, sizes
apply to both shapes, and both shapes paint without error.
Run: QT_QPA_PLATFORM=offscreen venv/Scripts/python -m pytest tests/test_widget_dock.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QPoint  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from src.config.constants import STATE_RECORDING, WIDGET_DOCK_BAR_WIDTH, WIDGET_DOCK_GLOW_PX, WIDGET_SIZES  # noqa: E402
from src.ui.widget import BAR_STRIP_MULTIPLIER, FloatingWidget  # noqa: E402

app = QApplication.instance() or QApplication([])
EDGE = app.primaryScreen().availableGeometry()
BAR_WINDOW = WIDGET_DOCK_BAR_WIDTH + WIDGET_DOCK_GLOW_PX
RIGHT = EDGE.x() + EDGE.width()


def _right_edge(w):
    return w.x() + w.width()


def test_docks_to_right_edge_and_drags_vertically_only():
    w = FloatingWidget("compact")
    assert _right_edge(w) == RIGHT
    assert w.width() == WIDGET_SIZES["compact"] * (1 + BAR_STRIP_MULTIPLIER)

    w.restore_position((5, 300))            # x in the tuple is ignored
    assert (w.x() + w.width(), w.y()) == (RIGHT, 300)

    w._drag_start_widget_pos = QPoint(w.x(), 300)
    w._dock(w._drag_start_widget_pos.y() + 120)   # what mouseMoveEvent does
    assert (w.x() + w.width(), w.y()) == (RIGHT, 420)

    w.restore_position((0, 10_000))         # clamped on screen
    assert w.y() == EDGE.y() + EDGE.height() - w.height()
    assert _right_edge(w) == RIGHT


def test_collapse_hover_and_resize():
    w = FloatingWidget("compact")
    seen = []
    w.collapsed_changed.connect(seen.append)

    w.set_collapsed(True)
    assert w.width() == BAR_WINDOW and _right_edge(w) == RIGHT
    assert seen == [True]
    assert not w.grab().isNull()            # bar paints

    w._set_hover_expanded(True)             # what enterEvent does
    assert w.width() == WIDGET_SIZES["compact"] * (1 + BAR_STRIP_MULTIPLIER)
    assert _right_edge(w) == RIGHT
    assert not w.grab().isNull()            # plate + circle paint

    w._set_hover_expanded(False)            # what leaveEvent does
    assert w.width() == BAR_WINDOW

    w.set_size("large")                     # size applies to the bar shape too
    assert w.height() == WIDGET_SIZES["large"]
    assert w.width() == BAR_WINDOW
    assert _right_edge(w) == RIGHT

    w.set_collapsed(False)
    assert w.width() == WIDGET_SIZES["large"] * (1 + BAR_STRIP_MULTIPLIER)
    assert seen == [True, False]


def test_collapse_animates_to_target_when_visible():
    from PyQt6.QtCore import QEventLoop, QTimer
    w = FloatingWidget("compact")
    w.show()
    full = w.width()
    w.set_collapsed(True)
    assert w.width() == full and w._slide == 1.0   # window shrinks only after the slide
    loop = QEventLoop()
    QTimer.singleShot(600, loop.quit)
    loop.exec()
    assert w._slide == 0.0
    assert w.width() == BAR_WINDOW and _right_edge(w) == RIGHT
    assert not w.grab().isNull()
    w.set_collapsed(False)
    assert w.width() == full and w._slide < 1.0    # window grows first, then slides in
    assert not w.grab().isNull()                   # mid-slide paint
    QTimer.singleShot(600, loop.quit)
    loop.exec()
    assert w._slide == 1.0 and _right_edge(w) == RIGHT

    # Recording glow paints on the collapsed bar
    w.set_collapsed(True)
    QTimer.singleShot(600, loop.quit)
    loop.exec()
    w.set_state(STATE_RECORDING)
    assert not w.grab().isNull()


if __name__ == "__main__":
    test_collapse_animates_to_target_when_visible()
    test_docks_to_right_edge_and_drags_vertically_only()
    test_collapse_hover_and_resize()
    print("ok")
