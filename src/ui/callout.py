"""Transcription callout popup — shows streaming text during processing."""

from PyQt6.QtWidgets import QWidget, QPlainTextEdit, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QPaintEvent, QFont, QTextCursor

from .styles import COLOR_BG_DARK, COLOR_WIDGET_RECORDING, COLOR_ACCENT
from ..config.logging_config import get_logger

logger = get_logger(__name__)

# Callout sizing (fractions of screen)
WIDTH_FRACTION = 1 / 5       # 1/5 of screen width
MAX_HEIGHT_FRACTION = 1 / 3  # max 1/3 of screen height
MIN_HEIGHT = 60              # minimum height in pixels
LINE_HEIGHT_ESTIMATE = 22    # rough pixels per line for auto-grow
PADDING = 12                 # inner padding
BORDER_RADIUS = 8
HIDE_DELAY_MS = 4000         # auto-hide after transcription complete


class TranscriptionCallout(QWidget):
    """Translucent popup showing streaming transcription segments."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._segments: list[str] = []
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._auto_hide)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize the callout window and text area."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(PADDING, PADDING, PADDING, PADDING)

        # Text display — read-only QPlainTextEdit with transparent bg
        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFrameStyle(0)  # No frame

        # Softer blue text (85% opacity of the recording blue)
        text_color = QColor(COLOR_WIDGET_RECORDING)
        text_color.setAlphaF(0.85)
        r, g, b, a = text_color.red(), text_color.green(), text_color.blue(), text_color.alpha()

        scrollbar_bg = COLOR_ACCENT
        scrollbar_handle = COLOR_WIDGET_RECORDING

        self._text_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background: transparent;
                color: rgba({r}, {g}, {b}, {a});
                font-family: "Segoe UI";
                font-size: 11pt;
                border: none;
                selection-background-color: rgba({r}, {g}, {b}, 60);
            }}
            QScrollBar:vertical {{
                background-color: {scrollbar_bg};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {scrollbar_handle};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        layout.addWidget(self._text_edit)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw translucent background with blue border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        bg = QColor(COLOR_BG_DARK)
        bg.setAlpha(230)  # ~90% opacity
        painter.setBrush(bg)

        # Border
        border = QColor(COLOR_WIDGET_RECORDING)
        border.setAlpha(150)
        painter.setPen(QPen(border, 1))

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, BORDER_RADIUS, BORDER_RADIUS)

    def _calculate_size(self) -> tuple[int, int]:
        """Calculate callout width and max height from screen geometry."""
        screen = QApplication.primaryScreen()
        if not screen:
            return (320, 200)
        geo = screen.availableGeometry()
        width = int(geo.width() * WIDTH_FRACTION)
        max_height = int(geo.height() * MAX_HEIGHT_FRACTION)
        return (width, max_height)

    def _auto_grow_height(self) -> None:
        """Grow height to fit content, up to max."""
        width, max_height = self._calculate_size()
        doc = self._text_edit.document()
        doc_height = int(doc.size().height()) + PADDING * 2 + 4
        new_height = max(MIN_HEIGHT, min(doc_height, max_height))
        if new_height != self.height():
            self.setFixedSize(width, new_height)
            # Re-check position stays on screen
            self._ensure_on_screen()

    def _ensure_on_screen(self) -> None:
        """Keep callout within screen bounds."""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        pos = self.pos()
        x, y = pos.x(), pos.y()

        if x + self.width() > geo.x() + geo.width():
            x = geo.x() + geo.width() - self.width() - 10
        if y + self.height() > geo.y() + geo.height():
            y = geo.y() + geo.height() - self.height() - 10
        if x < geo.x():
            x = geo.x() + 10
        if y < geo.y():
            y = geo.y() + 10

        self.move(x, y)

    def show_at_widget(self, widget_pos: QPoint, widget_size: int) -> None:
        """Position and show callout near the floating widget."""
        width, max_height = self._calculate_size()
        self.setFixedSize(width, MIN_HEIGHT)

        # Position below and to the left of the widget
        x = widget_pos.x() + widget_size // 2 - width // 2
        y = widget_pos.y() + widget_size + 8

        self.move(x, y)
        self._ensure_on_screen()
        self.show()
        logger.debug("Callout shown at widget position (%d, %d)", x, y)

    def show_near_tray(self) -> None:
        """Position and show callout near the system tray (bottom-right)."""
        width, max_height = self._calculate_size()
        self.setFixedSize(width, MIN_HEIGHT)

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + geo.width() - width - 20
            y = geo.y() + geo.height() - MIN_HEIGHT - 60  # above taskbar
        else:
            x, y = 100, 100

        self.move(x, y)
        self.show()
        logger.debug("Callout shown near tray at (%d, %d)", x, y)

    def append_segment(self, text: str) -> None:
        """Append a transcription segment and auto-scroll."""
        text = text.strip()
        if not text:
            return

        self._segments.append(text)

        # Append to text display
        cursor = self._text_edit.textCursor()
        if not self._text_edit.toPlainText():
            cursor.insertText(text)
        else:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(" " + text)

        # Auto-scroll to bottom
        self._text_edit.moveCursor(QTextCursor.MoveOperation.End)
        self._text_edit.ensureCursorVisible()

        # Grow height to fit
        self._auto_grow_height()

    def set_final_text(self, text: str) -> None:
        """Replace streaming segments with final cleaned text."""
        self._text_edit.setPlainText(text)
        self._text_edit.moveCursor(QTextCursor.MoveOperation.End)
        self._auto_grow_height()

        # Start auto-hide timer
        self._hide_timer.start(HIDE_DELAY_MS)

    def clear(self) -> None:
        """Clear text and hide."""
        self._hide_timer.stop()
        self._segments.clear()
        self._text_edit.clear()
        self.hide()

    def get_text(self) -> str:
        """Get current callout text (for manual paste fallback)."""
        return self._text_edit.toPlainText()

    def show_paste_warning(self, text: str) -> None:
        """Show warning that auto-paste failed, keep text available."""
        self._hide_timer.stop()
        self._text_edit.setPlainText(text + "\n\n[Target window unavailable — text copied to clipboard, paste manually]")
        self._text_edit.moveCursor(QTextCursor.MoveOperation.End)
        self._auto_grow_height()
        # Longer display time for manual paste scenario
        self._hide_timer.start(HIDE_DELAY_MS * 3)

    def _auto_hide(self) -> None:
        """Auto-hide after delay."""
        self.clear()
        logger.debug("Callout auto-hidden")
