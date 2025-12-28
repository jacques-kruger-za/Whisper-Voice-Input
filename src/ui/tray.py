"""System tray integration."""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import pyqtSignal, QObject, QPointF, QRectF, Qt

from ..config.constants import APP_NAME, STATE_IDLE, STATE_RECORDING, STATE_PROCESSING, STATE_ERROR
from .styles import COLOR_TRAY_IDLE, COLOR_TRAY_RECORDING, COLOR_TRAY_PROCESSING, COLOR_TRAY_ERROR


class TrayIcon(QObject):
    """System tray icon with context menu."""

    # Signals
    toggle_recording = pyqtSignal()
    show_widget = pyqtSignal()
    hide_widget = pyqtSignal()
    open_settings = pyqtSignal()
    quit_app = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tray = QSystemTrayIcon(parent)
        self._state = STATE_IDLE
        self._widget_visible = True
        self._setup_icons()
        self._setup_menu()
        self._update_icon()

    def _setup_icons(self) -> None:
        """Create icons for different states with darker colors for taskbar visibility."""
        self._icons = {}
        for state, color in [
            (STATE_IDLE, COLOR_TRAY_IDLE),
            (STATE_RECORDING, COLOR_TRAY_RECORDING),
            (STATE_PROCESSING, COLOR_TRAY_PROCESSING),
            (STATE_ERROR, COLOR_TRAY_ERROR),
        ]:
            self._icons[state] = self._create_icon(color)

    def _create_icon(self, color: str, size: int = 64) -> QIcon:
        """Create a bold, thick condenser microphone icon for maximum taskbar visibility."""
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = size / 2
        icon_color = QColor(color)

        # Minimal margins for maximum size
        margin = size * 0.04
        available_height = size - (2 * margin)

        # Bold proportions - wider and taller
        head_height = available_height * 0.45
        head_width = head_height * 0.85  # Wider head
        head_x = center_x - head_width / 2
        head_y = margin

        # MUCH thicker lines for visibility
        line_width = max(4.0, size / 12)  # Much thicker

        # Filled mic head - bold and solid
        painter.setBrush(icon_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(
            QRectF(head_x, head_y, head_width, head_height),
            head_width / 2, head_width / 2
        )

        # Cut out horizontal slots (3 dark lines) - thicker slots
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)

        slot_width = head_width * 0.5
        slot_height = max(3, head_height * 0.08)  # Thicker slots
        slot_x = center_x - slot_width / 2
        slot_spacing = head_height * 0.18

        for i in range(3):
            slot_y = head_y + head_height * 0.26 + i * slot_spacing
            painter.drawRoundedRect(
                QRectF(slot_x, slot_y, slot_width, slot_height),
                slot_height / 2, slot_height / 2
            )

        # Reset composition mode
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # Thick cradle/mount arc
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pen = QPen(icon_color, line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        cradle_width = head_width * 1.3
        cradle_height = head_height * 0.55
        cradle_x = center_x - cradle_width / 2
        cradle_y = head_y + head_height - cradle_height * 0.25

        painter.drawArc(
            QRectF(cradle_x, cradle_y, cradle_width, cradle_height),
            0, -180 * 16
        )

        # Thick stand
        stand_top = cradle_y + cradle_height / 2
        stand_bottom = margin + available_height * 0.88
        painter.drawLine(
            QPointF(center_x, stand_top),
            QPointF(center_x, stand_bottom)
        )

        # Thick base
        base_width = head_width * 1.0
        painter.drawLine(
            QPointF(center_x - base_width / 2, stand_bottom),
            QPointF(center_x + base_width / 2, stand_bottom)
        )

        painter.end()
        return QIcon(pixmap)

    def _setup_menu(self) -> None:
        """Create the context menu."""
        self._menu = QMenu()

        # Record action
        self._record_action = self._menu.addAction("Start Recording")
        self._record_action.triggered.connect(self.toggle_recording.emit)

        self._menu.addSeparator()

        # Widget visibility
        self._widget_action = self._menu.addAction("Hide Widget")
        self._widget_action.triggered.connect(self._toggle_widget)

        # Settings
        settings_action = self._menu.addAction("Settings")
        settings_action.triggered.connect(self.open_settings.emit)

        self._menu.addSeparator()

        # Quit
        quit_action = self._menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_app.emit)

        self._tray.setContextMenu(self._menu)

        # Left click to toggle recording
        self._tray.activated.connect(self._on_activated)

    def _toggle_widget(self) -> None:
        """Toggle widget visibility."""
        if self._widget_visible:
            self.hide_widget.emit()
        else:
            self.show_widget.emit()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Left click - toggle recording
            self.toggle_recording.emit()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            # Middle click - toggle widget
            self._toggle_widget()

    def set_state(self, state: str) -> None:
        """Update icon and menu based on state."""
        self._state = state
        self._update_icon()
        self._update_menu()

    def _update_icon(self) -> None:
        """Update tray icon based on state."""
        icon = self._icons.get(self._state, self._icons[STATE_IDLE])
        self._tray.setIcon(icon)

        # Update tooltip
        tooltips = {
            STATE_IDLE: f"{APP_NAME} - Ready",
            STATE_RECORDING: f"{APP_NAME} - Recording...",
            STATE_PROCESSING: f"{APP_NAME} - Processing...",
            STATE_ERROR: f"{APP_NAME} - Error",
        }
        self._tray.setToolTip(tooltips.get(self._state, APP_NAME))

    def _update_menu(self) -> None:
        """Update menu text based on state."""
        if self._state == STATE_RECORDING:
            self._record_action.setText("Stop Recording")
        else:
            self._record_action.setText("Start Recording")

    def set_widget_visible(self, visible: bool) -> None:
        """Update widget visibility state."""
        self._widget_visible = visible
        if visible:
            self._widget_action.setText("Hide Widget")
        else:
            self._widget_action.setText("Show Widget")

    def show(self) -> None:
        """Show the tray icon."""
        self._tray.show()

    def hide(self) -> None:
        """Hide the tray icon."""
        self._tray.hide()

    def show_message(self, title: str, message: str, duration: int = 3000) -> None:
        """Show a balloon notification."""
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, duration)

    def is_visible(self) -> bool:
        """Check if tray icon is visible."""
        return self._tray.isVisible()
