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

from src.config.constants import WIDGET_DOCK_BAR_WIDTH, WIDGET_SIZES  # noqa: E402
from src.ui.widget import BAR_STRIP_MULTIPLIER, FloatingWidget  # noqa: E402

app = QApplication.instance() or QApplication([])
EDGE = app.primaryScreen().availableGeometry()
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
    assert w.width() == WIDGET_DOCK_BAR_WIDTH and _right_edge(w) == RIGHT
    assert seen == [True]
    assert not w.grab().isNull()            # bar paints

    w._set_hover_expanded(True)             # what enterEvent does
    assert w.width() == WIDGET_SIZES["compact"] * (1 + BAR_STRIP_MULTIPLIER)
    assert _right_edge(w) == RIGHT
    assert not w.grab().isNull()            # plate + circle paint

    w._set_hover_expanded(False)            # what leaveEvent does
    assert w.width() == WIDGET_DOCK_BAR_WIDTH

    w.set_size("large")                     # size applies to the bar shape too
    assert w.height() == WIDGET_SIZES["large"]
    assert w.width() == WIDGET_DOCK_BAR_WIDTH
    assert _right_edge(w) == RIGHT

    w.set_collapsed(False)
    assert w.width() == WIDGET_SIZES["large"] * (1 + BAR_STRIP_MULTIPLIER)
    assert seen == [True, False]


if __name__ == "__main__":
    test_docks_to_right_edge_and_drags_vertically_only()
    test_collapse_hover_and_resize()
    print("ok")
