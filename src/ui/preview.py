"""Streaming preview — text that streams out of the docked widget.

A glimpse of what Whisper is hearing right now. Not interactive. Updates per
streaming round; fades when an utterance finalizes and lands in the editor.

Visual identity:
- Anchored to the widget: right edge sits just left of the widget's window,
  vertically centred on it. Text is right-aligned so the newest words are
  nearest the widget and the block grows LEFT as more arrives, up to a cap
  of one fifth of the screen width, then wraps.
- PREVIEW_VISIBLE_LINES at full opacity; one older line above fades out.
- No panel. A very faint glow in the widget's active colour sits behind the
  text, strongest at the widget side and dissolving leftward.
- Frameless, no focus, click-through.
- Falls back to the bottom-right of the screen when the widget is hidden.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QPropertyAnimation, QRectF, QRect
from PyQt6.QtGui import (
    QColor, QPainter, QPaintEvent, QFont, QFontMetrics, QLinearGradient,
    QGuiApplication, QPalette,
)
from PyQt6.QtWidgets import QWidget, QApplication

from ..config.logging_config import get_logger
from .styles import COLOR_WIDGET_RECORDING

logger = get_logger(__name__)


# Visual tuning — kept module-level so they're easy to find when tuning.
PREVIEW_WIDTH_FRACTION = 0.20      # cap: one fifth of the screen
PREVIEW_FONT_SIZE_PT = 11
PREVIEW_PADDING_PX = 10
PREVIEW_LINE_SPACING_PX = 2        # extra px between wrapped lines
PREVIEW_GAP_PX = 6                 # gap between text block and the widget
PREVIEW_TEXT_ALPHA = 230
PREVIEW_VISIBLE_LINES = 2          # lines shown at full opacity
PREVIEW_FADE_LINES = 1             # older lines rendered above, fading out
PREVIEW_FADE_OUT_MS = 600          # length of the disappear animation
PREVIEW_SCREEN_MARGIN_PX = 16      # gap from the screen edges (fallback anchor)
PREVIEW_GLOW_ALPHA = 0.16          # peak alpha of the accent glow, widget side
PREVIEW_TEXT_LIGHT_MODE = (70, 70, 75)       # dark grey on a light desktop
PREVIEW_TEXT_DARK_MODE = (200, 200, 205)     # light grey on a dark desktop


class StreamingPreviewWindow(QWidget):
    """Floating preview for live streaming transcription text."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text: str = ""
        self._lines: list[str] = []
        self._anchor: QWidget | None = None
        self._fade_anim: QPropertyAnimation | None = None
        self._setup_window()
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

    # ── Public API ────────────────────────────────────────────────────────

    def set_anchor(self, widget: QWidget | None) -> None:
        """Widget the text streams out of. Re-read on every update so a
        dragged or collapsed widget keeps its preview attached."""
        self._anchor = widget

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
        self._layout()
        if not self.isVisible():
            self.show()
        self.update()

    def clear(self) -> None:
        """Clear text without animating."""
        self._text = ""
        self._lines = []
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
        self._lines = []
        self.setWindowOpacity(1.0)
        self._fade_anim = None

    # ── Layout helpers ────────────────────────────────────────────────────

    def _font(self) -> QFont:
        f = QFont()
        f.setPointSize(PREVIEW_FONT_SIZE_PT)
        return f

    def _line_height(self) -> int:
        return QFontMetrics(self._font()).height() + PREVIEW_LINE_SPACING_PX

    @staticmethod
    def _max_lines_rendered() -> int:
        return PREVIEW_VISIBLE_LINES + PREVIEW_FADE_LINES

    @staticmethod
    def _screen_rect() -> QRect:
        screen = QApplication.primaryScreen()
        return screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

    def _max_inner_width(self) -> int:
        return max(1, int(self._screen_rect().width() * PREVIEW_WIDTH_FRACTION) - PREVIEW_PADDING_PX * 2)

    def _wrap_lines(self, inner_w: int) -> list[str]:
        """Word-wrap the current text into lines that fit inner_w."""
        if not self._text:
            return []
        fm = QFontMetrics(self._font())
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

    def _layout(self) -> None:
        """Size to the (last few) wrapped lines and pin next to the anchor."""
        fm = QFontMetrics(self._font())
        inner_max = self._max_inner_width()
        self._lines = self._wrap_lines(inner_max)[-self._max_lines_rendered():]
        content_w = max((fm.horizontalAdvance(line) for line in self._lines), default=1)
        width = min(inner_max, content_w) + PREVIEW_PADDING_PX * 2
        height = self._line_height() * max(1, len(self._lines)) + PREVIEW_PADDING_PX * 2
        self.setFixedSize(width, height)

        screen = self._screen_rect()
        anchor = self._anchor if (self._anchor is not None and self._anchor.isVisible()) else None
        if anchor is not None:
            geo = anchor.geometry()
            x = geo.x() - PREVIEW_GAP_PX - width
            y = geo.y() + geo.height() // 2 - height // 2
        else:
            x = screen.x() + screen.width() - width - PREVIEW_SCREEN_MARGIN_PX
            y = screen.y() + screen.height() - height - PREVIEW_SCREEN_MARGIN_PX
        x = max(screen.x(), min(x, screen.x() + screen.width() - width))
        y = max(screen.y(), min(y, screen.y() + screen.height() - height))
        self.move(x, y)

    # ── Colours ───────────────────────────────────────────────────────────

    @staticmethod
    def _system_is_dark() -> bool:
        scheme = QGuiApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
        return QApplication.palette().color(QPalette.ColorRole.Window).lightness() < 128

    def _text_color(self) -> QColor:
        return QColor(*(PREVIEW_TEXT_DARK_MODE if self._system_is_dark() else PREVIEW_TEXT_LIGHT_MODE))

    # ── Painting ──────────────────────────────────────────────────────────

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        if not self._lines:
            return

        # Faint accent glow: strongest at the widget (right) side, dissolving
        # leftward, so the text reads as emanating from the widget.
        rect = QRectF(self.rect())
        accent = QColor(COLOR_WIDGET_RECORDING)
        glow = QLinearGradient(rect.left(), 0, rect.right(), 0)
        clear = QColor(accent)
        clear.setAlphaF(0.0)
        peak = QColor(accent)
        peak.setAlphaF(PREVIEW_GLOW_ALPHA)
        glow.setColorAt(0.0, clear)
        glow.setColorAt(1.0, peak)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        radius = rect.height() / 2
        painter.drawRoundedRect(rect, radius, radius)

        font = self._font()
        painter.setFont(font)
        fm = QFontMetrics(font)
        line_h = self._line_height()

        text_color = self._text_color()
        # Bare text needs a whisper of contrast against whatever is behind it.
        shadow_color = QColor(255, 255, 255) if text_color.lightness() < 128 else QColor(0, 0, 0)

        right = self.width() - PREVIEW_PADDING_PX
        bottom_y = self.height() - PREVIEW_PADDING_PX

        # Draw lines from bottom upward, right-aligned so the newest words
        # sit against the widget.
        for idx_from_bottom, line in enumerate(reversed(self._lines)):
            baseline = bottom_y - idx_from_bottom * line_h - fm.descent()
            x = right - fm.horizontalAdvance(line)
            if idx_from_bottom < PREVIEW_VISIBLE_LINES:
                alpha = PREVIEW_TEXT_ALPHA
            else:
                fade_idx = idx_from_bottom - PREVIEW_VISIBLE_LINES + 1
                ratio = max(0.0, 1.0 - fade_idx / (PREVIEW_FADE_LINES + 1))
                alpha = int(PREVIEW_TEXT_ALPHA * ratio)
            s = QColor(shadow_color)
            s.setAlpha(alpha // 3)
            painter.setPen(s)
            painter.drawText(int(x) + 1, int(baseline) + 1, line)
            c = QColor(text_color)
            c.setAlpha(alpha)
            painter.setPen(c)
            painter.drawText(int(x), int(baseline), line)
