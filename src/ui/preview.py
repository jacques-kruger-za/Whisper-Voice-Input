"""Streaming preview window — translucent text panel in the bottom-right.

A glimpse of what Whisper is hearing right now. Not interactive. Updates per
streaming round; clears (with fade) when an utterance finalizes and lands in
the user's editor.

Visual identity:
- Fixed position: bottom-right of the primary screen
- Fixed width: one fifth of the screen width
- Text wraps; panel grows UPWARDS as more lines arrive
- Three lines are shown at full opacity. Anything above that fades out at
  the top edge so older content dissolves rather than cuts off
- Frameless, no border (subtle), no focus, doesn't steal click events
- Position is independent of the floating recorder widget
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QPropertyAnimation, QRectF, QPoint
from PyQt6.QtGui import (
    QColor, QPainter, QPaintEvent, QPainterPath, QFont, QFontMetrics,
    QLinearGradient, QPen,
)
from PyQt6.QtWidgets import QWidget, QApplication

from ..config.logging_config import get_logger

logger = get_logger(__name__)


# Visual tuning — kept module-level so they're easy to find when tuning.
PREVIEW_WIDTH_FRACTION = 0.20      # one fifth of the screen
PREVIEW_FONT_SIZE_PT = 11
PREVIEW_PADDING_PX = 12
PREVIEW_LINE_SPACING_PX = 2        # extra px between wrapped lines
PREVIEW_BORDER_RADIUS = 10
PREVIEW_BG_ALPHA = 200             # 0..255 — translucent
PREVIEW_TEXT_ALPHA = 230
PREVIEW_VISIBLE_LINES = 3          # lines shown at full opacity
PREVIEW_FADE_LINES = 2             # extra lines rendered above, fading out
PREVIEW_FADE_OUT_MS = 600          # length of the disappear animation
PREVIEW_SCREEN_MARGIN_PX = 16      # gap from the screen edges


class StreamingPreviewWindow(QWidget):
    """Floating preview panel for live streaming transcription text."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text: str = ""
        self._fade_anim: QPropertyAnimation | None = None
        self._setup_window()
        self._apply_fixed_width()
        self.hide()

    # ── Window setup ──────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        # Frameless, top-most, doesn't take focus or appear in taskbar.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput  # click-through
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _apply_fixed_width(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            self.setFixedWidth(320)
            return
        geo = screen.availableGeometry()
        self.setFixedWidth(int(geo.width() * PREVIEW_WIDTH_FRACTION))

    # ── Public API ────────────────────────────────────────────────────────

    def set_text(self, text: str) -> None:
        """Update the preview content. Called per streaming round.

        Empty text hides the panel — there's no point showing an empty box.
        """
        new_text = (text or "").strip()
        self._text = new_text
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None
        if not new_text:
            self.hide()
            self.setWindowOpacity(1.0)
            return
        self.setWindowOpacity(1.0)
        self._resize_for_text()
        self._anchor_bottom_right()
        if not self.isVisible():
            self.show()
        self.update()

    def clear(self) -> None:
        """Clear text without animating."""
        self._text = ""
        self.update()

    def fade_out(self) -> None:
        """Start a fade-out animation."""
        if not self.isVisible():
            return
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
        self.setWindowOpacity(1.0)
        self._fade_anim = None

    def position_near_widget(self, widget_pos: QPoint, widget_w: int, widget_h: int) -> None:
        """Kept for backwards-compatibility with callers. Position is now
        independent of the recorder widget — always bottom-right of screen.
        """
        self._apply_fixed_width()
        self._anchor_bottom_right()

    # ── Layout helpers ────────────────────────────────────────────────────

    def _font(self) -> QFont:
        f = QFont()
        f.setPointSize(PREVIEW_FONT_SIZE_PT)
        return f

    def _wrap_lines(self) -> list[str]:
        """Word-wrap the current text into lines that fit the inner width."""
        if not self._text:
            return []
        fm = QFontMetrics(self._font())
        inner_w = max(1, self.width() - PREVIEW_PADDING_PX * 2)
        words = self._text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else current + " " + word
            if fm.horizontalAdvance(candidate) <= inner_w:
                current = candidate
            else:
                if current:
                    lines.append(current)
                # If a single word exceeds the width, hard-break it.
                if fm.horizontalAdvance(word) > inner_w:
                    chunk = ""
                    for ch in word:
                        if fm.horizontalAdvance(chunk + ch) <= inner_w:
                            chunk += ch
                        else:
                            lines.append(chunk)
                            chunk = ch
                    current = chunk
                else:
                    current = word
        if current:
            lines.append(current)
        return lines

    def _line_height(self) -> int:
        return QFontMetrics(self._font()).height() + PREVIEW_LINE_SPACING_PX

    def _max_lines_rendered(self) -> int:
        return PREVIEW_VISIBLE_LINES + PREVIEW_FADE_LINES

    # ── Sizing & positioning ──────────────────────────────────────────────

    def _resize_for_text(self) -> None:
        """Grow height upward to fit wrapped lines, capped at visible+fade."""
        lines = self._wrap_lines()
        n = min(len(lines), self._max_lines_rendered()) if lines else 1
        h = self._line_height() * n + PREVIEW_PADDING_PX * 2
        self.setFixedHeight(h)

    def _anchor_bottom_right(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        x = geo.x() + geo.width() - self.width() - PREVIEW_SCREEN_MARGIN_PX
        y = geo.y() + geo.height() - self.height() - PREVIEW_SCREEN_MARGIN_PX
        self.move(x, y)

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

        # Subtle border
        border = QColor(120, 180, 255)
        border.setAlpha(60)
        painter.setPen(QPen(border, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, PREVIEW_BORDER_RADIUS, PREVIEW_BORDER_RADIUS)

        if not self._text:
            return

        # Clip everything that follows to the rounded rect so the gradient
        # and text don't bleed past the corners.
        clip_path = QPainterPath()
        clip_path.addRoundedRect(rect, PREVIEW_BORDER_RADIUS, PREVIEW_BORDER_RADIUS)
        painter.setClipPath(clip_path)

        font = self._font()
        painter.setFont(font)
        fm = QFontMetrics(font)
        line_h = self._line_height()

        # Pick the most recent (visible + fade) lines so older content
        # naturally rolls off the top.
        all_lines = self._wrap_lines()
        max_n = self._max_lines_rendered()
        lines = all_lines[-max_n:]

        text_color = QColor(225, 230, 240)

        inner_left = PREVIEW_PADDING_PX
        bottom_y = self.height() - PREVIEW_PADDING_PX

        # Draw lines from bottom upward.
        n = len(lines)
        for idx_from_bottom, line in enumerate(reversed(lines)):
            baseline = bottom_y - idx_from_bottom * line_h - fm.descent()
            # idx_from_bottom 0 is the newest (bottom) line; visible lines
            # are 0..PREVIEW_VISIBLE_LINES-1; older lines fade based on
            # how far past the visible window they are.
            if idx_from_bottom < PREVIEW_VISIBLE_LINES:
                alpha = PREVIEW_TEXT_ALPHA
            else:
                fade_idx = idx_from_bottom - PREVIEW_VISIBLE_LINES + 1
                # Linear fade across PREVIEW_FADE_LINES steps.
                ratio = max(0.0, 1.0 - fade_idx / (PREVIEW_FADE_LINES + 1))
                alpha = int(PREVIEW_TEXT_ALPHA * ratio)
            c = QColor(text_color)
            c.setAlpha(alpha)
            painter.setPen(c)
            painter.drawText(int(inner_left), int(baseline), line)

        # Top fade gradient: dissolves anything above the visible window.
        # Only paint it when we actually have overflow rendered above.
        if n > PREVIEW_VISIBLE_LINES:
            fade_h = line_h * PREVIEW_FADE_LINES + PREVIEW_PADDING_PX
            fade_rect = QRectF(rect.left(), rect.top(), rect.width(), fade_h)
            gradient = QLinearGradient(0, fade_rect.top(), 0, fade_rect.bottom())
            bg_solid = QColor(bg)
            bg_solid.setAlpha(PREVIEW_BG_ALPHA)
            bg_clear = QColor(bg)
            bg_clear.setAlpha(0)
            gradient.setColorAt(0.0, bg_solid)
            gradient.setColorAt(1.0, bg_clear)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawRect(fade_rect)
