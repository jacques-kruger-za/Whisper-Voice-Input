"""Streaming preview window — translucent text panel rolling out of the widget.

A glimpse of what Whisper is hearing right now. Not interactive. Updates per
streaming round; clears (with fade) when an utterance finalizes and lands in
the user's editor.

Visual identity:
- Translucent rounded panel anchored to the LEFT of the floating widget
- Text appears on the right side (closest to the widget)
- Linear fade-out gradient on the LEFT edge so older text dissolves rather
  than cuts off
- Width grows from a minimum (~5cm) up to half the screen, then text past
  the visible area fades out completely on the left
- Frameless, no border, no focus, doesn't steal click events
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QRectF, QTimer, pyqtProperty
from PyQt6.QtGui import (
    QColor, QPainter, QPaintEvent, QPainterPath, QFont, QFontMetrics,
    QLinearGradient, QPen,
)
from PyQt6.QtWidgets import QWidget, QApplication

from ..config.logging_config import get_logger

logger = get_logger(__name__)


# Visual tuning — kept module-level so they're easy to find when tuning.
PREVIEW_HEIGHT_PX = 56          # single line, comfortable padding
PREVIEW_MIN_WIDTH_PX = 200      # ~5 cm at 96 dpi
PREVIEW_MAX_WIDTH_FRACTION = 0.5  # half the screen
PREVIEW_FONT_SIZE_PT = 11
PREVIEW_PADDING_PX = 12
PREVIEW_BORDER_RADIUS = 10
PREVIEW_BG_ALPHA = 200          # 0..255 — translucent
PREVIEW_TEXT_ALPHA = 230
PREVIEW_FADE_WIDTH_PX = 80      # left-edge fade gradient width
PREVIEW_FADE_OUT_MS = 600       # length of the disappear animation
PREVIEW_GAP_FROM_WIDGET_PX = 8


class StreamingPreviewWindow(QWidget):
    """Floating preview panel for live streaming transcription text."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text: str = ""
        # Window opacity drives the fade-out animation. Property animation
        # rather than QGraphicsOpacityEffect to avoid the cost of an
        # off-screen render of the (already cheap) painted content.
        self._target_opacity: float = 1.0
        self._fade_anim: QPropertyAnimation | None = None
        self._setup_window()
        self.hide()

    # ── Window setup ──────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        # Frameless, top-most, doesn't take focus or appear in taskbar.
        # WA_ShowWithoutActivating + Tool ensures clicking it doesn't pull
        # focus away from the user's editor mid-dictation.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput  # click-through
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedHeight(PREVIEW_HEIGHT_PX)
        self.resize(PREVIEW_MIN_WIDTH_PX, PREVIEW_HEIGHT_PX)

    # ── Public API ────────────────────────────────────────────────────────

    def set_text(self, text: str) -> None:
        """Update the preview content. Called per streaming round.

        Cancels any pending fade-out so subsequent updates re-show the
        panel at full opacity even if a fade-out was scheduled.
        """
        self._text = (text or "").strip()
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None
        self.setWindowOpacity(1.0)
        self._resize_for_text()
        if not self.isVisible():
            self.show()
        self.update()

    def clear(self) -> None:
        """Clear text without animating."""
        self._text = ""
        self.update()

    def fade_out(self) -> None:
        """Start a fade-out animation. The panel will become invisible at
        the end of PREVIEW_FADE_OUT_MS and clear its text.
        """
        if not self.isVisible():
            return
        # Stop any in-flight animation first so we can chain cleanly.
        if self._fade_anim is not None:
            self._fade_anim.stop()
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(PREVIEW_FADE_OUT_MS)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(0.0)
        anim.finished.connect(self._on_fade_finished)
        anim.start()
        self._fade_anim = anim

    def _on_fade_finished(self) -> None:
        self.hide()
        self._text = ""
        self.setWindowOpacity(1.0)  # ready for next show()
        self._fade_anim = None

    def position_near_widget(self, widget_pos: QPoint, widget_w: int, widget_h: int) -> None:
        """Anchor preview to the LEFT of the floating widget, vertically
        centred. Width grows toward the left edge of the screen as text
        accumulates.
        """
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()

        # Right edge of preview = left edge of widget - gap
        right_edge = widget_pos.x() - PREVIEW_GAP_FROM_WIDGET_PX
        # Vertical centre on the widget's centre
        y = widget_pos.y() + (widget_h - PREVIEW_HEIGHT_PX) // 2

        # Clamp y on screen
        if y < geo.y() + 4:
            y = geo.y() + 4
        if y + PREVIEW_HEIGHT_PX > geo.y() + geo.height() - 4:
            y = geo.y() + geo.height() - PREVIEW_HEIGHT_PX - 4

        # Use the current width (may grow on text update)
        x = right_edge - self.width()
        # Clamp x — don't go off the left edge of the screen
        if x < geo.x() + 4:
            x = geo.x() + 4
        self.move(x, y)

    # ── Sizing ────────────────────────────────────────────────────────────

    def _resize_for_text(self) -> None:
        """Grow width to fit the text up to PREVIEW_MAX_WIDTH_FRACTION of
        the screen. Beyond that, text overflows on the left under the
        fade gradient.

        Anchored on the RIGHT — keeps the right edge stable so the panel
        appears to grow leftward away from the widget.
        """
        screen = QApplication.primaryScreen()
        max_w = PREVIEW_MIN_WIDTH_PX
        if screen:
            max_w = max(
                PREVIEW_MIN_WIDTH_PX,
                int(screen.availableGeometry().width() * PREVIEW_MAX_WIDTH_FRACTION),
            )

        font = QFont()
        font.setPointSize(PREVIEW_FONT_SIZE_PT)
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self._text) if self._text else 0
        target = min(max_w, max(PREVIEW_MIN_WIDTH_PX, text_w + PREVIEW_PADDING_PX * 2))

        if target == self.width():
            return
        old_right = self.x() + self.width()
        self.setFixedWidth(target)
        # Re-anchor so the RIGHT edge stays in place — preview grows leftward.
        self.move(old_right - target, self.y())

    # ── Painting ──────────────────────────────────────────────────────────

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        # Rounded translucent background
        bg = QColor(20, 22, 28)
        bg.setAlpha(PREVIEW_BG_ALPHA)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, PREVIEW_BORDER_RADIUS, PREVIEW_BORDER_RADIUS)

        # Subtle border — same color family as widget recording state
        border = QColor(120, 180, 255)
        border.setAlpha(60)
        painter.setPen(QPen(border, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, PREVIEW_BORDER_RADIUS, PREVIEW_BORDER_RADIUS)

        if not self._text:
            return

        # Text: right-aligned so the most recent words sit closest to the
        # widget, and older content trails off to the left under the fade.
        font = QFont()
        font.setPointSize(PREVIEW_FONT_SIZE_PT)
        painter.setFont(font)

        text_color = QColor(225, 230, 240)
        text_color.setAlpha(PREVIEW_TEXT_ALPHA)
        painter.setPen(text_color)

        text_rect = self.rect().adjusted(
            PREVIEW_PADDING_PX, 0,
            -PREVIEW_PADDING_PX, 0,
        )
        # ElideLeft so when the text is wider than the panel, the LEFT
        # (oldest) end gets truncated with an ellipsis under the fade —
        # gives the impression of older words rolling off the left.
        fm = QFontMetrics(font)
        elided = fm.elidedText(self._text, Qt.TextElideMode.ElideLeft, text_rect.width())
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
            elided,
        )

        # Left-edge fade gradient: alpha mask making the leftmost
        # PREVIEW_FADE_WIDTH_PX pixels dissolve. Drawn LAST as a
        # rectangle in the same colour as the background, with a horizontal
        # alpha gradient (opaque on the far left → transparent inwards).
        # Using DestinationOut composition mode would punch through but
        # that requires premultiplied alpha — easier to over-paint with
        # the panel's own bg colour here.
        fade_rect = QRectF(
            rect.left(), rect.top(),
            min(PREVIEW_FADE_WIDTH_PX, rect.width()),
            rect.height(),
        )
        gradient = QLinearGradient(
            fade_rect.left(), 0, fade_rect.right(), 0,
        )
        bg_solid = QColor(bg)
        bg_solid.setAlpha(PREVIEW_BG_ALPHA)  # full panel bg on far left
        bg_clear = QColor(bg)
        bg_clear.setAlpha(0)
        gradient.setColorAt(0.0, bg_solid)
        gradient.setColorAt(1.0, bg_clear)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        # Clip to the rounded rect so the gradient doesn't paint over the
        # rounded corner outline.
        clip_path = QPainterPath()
        clip_path.addRoundedRect(rect, PREVIEW_BORDER_RADIUS, PREVIEW_BORDER_RADIUS)
        painter.setClipPath(clip_path)
        painter.drawRect(fade_rect)
