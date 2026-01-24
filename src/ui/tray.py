"""System tray integration."""

import os
import sys
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import pyqtSignal, QObject

from ..config.constants import APP_NAME, STATE_IDLE, STATE_RECORDING, STATE_PROCESSING, STATE_ERROR
from ..config.logging_config import get_logger

logger = get_logger(__name__)


def get_assets_dir() -> str:
    """Get the assets directory path, works for both dev and PyInstaller."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running in development
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, 'assets')


ASSETS_DIR = get_assets_dir()


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
        logger.debug("Initializing TrayIcon")
        self._tray = QSystemTrayIcon(parent)
        self._state = STATE_IDLE
        self._widget_visible = True
        self._setup_icons()
        self._setup_menu()
        self._update_icon()
        logger.debug("TrayIcon initialized successfully")

    def _setup_icons(self) -> None:
        """Load PNG icons for different states from assets folder."""
        logger.debug("Loading tray icons from %s", ASSETS_DIR)
        self._icons = {
            STATE_IDLE: QIcon(os.path.join(ASSETS_DIR, 'mic_ico_grey_tray.png')),
            STATE_RECORDING: QIcon(os.path.join(ASSETS_DIR, 'mic_ico_blue_tray.png')),
            STATE_PROCESSING: QIcon(os.path.join(ASSETS_DIR, 'mic_ico_orange_tray.png')),
            STATE_ERROR: QIcon(os.path.join(ASSETS_DIR, 'mic_ico_red_tray.png')),
        }
        logger.debug("Tray icons loaded for %d states", len(self._icons))

    def _setup_menu(self) -> None:
        """Create the context menu."""
        logger.debug("Setting up tray context menu")
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
        logger.debug("Tray context menu setup complete")

    def _toggle_widget(self) -> None:
        """Toggle widget visibility."""
        logger.debug("Toggling widget visibility (currently visible=%s)", self._widget_visible)
        if self._widget_visible:
            self.hide_widget.emit()
        else:
            self.show_widget.emit()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        logger.debug("Tray icon activated with reason: %s", reason)
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Left click - toggle recording
            logger.debug("Left click detected, emitting toggle_recording signal")
            self.toggle_recording.emit()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            # Middle click - toggle widget
            logger.debug("Middle click detected, toggling widget")
            self._toggle_widget()

    def set_state(self, state: str) -> None:
        """Update icon and menu based on state."""
        logger.debug("Setting tray state: %s", state)
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
        tooltip = tooltips.get(self._state, APP_NAME)
        self._tray.setToolTip(tooltip)
        logger.debug("Updated tray icon and tooltip for state: %s", self._state)

    def _update_menu(self) -> None:
        """Update menu text based on state."""
        if self._state == STATE_RECORDING:
            self._record_action.setText("Stop Recording")
        else:
            self._record_action.setText("Start Recording")

    def set_widget_visible(self, visible: bool) -> None:
        """Update widget visibility state."""
        logger.debug("Setting widget visibility state: %s", visible)
        self._widget_visible = visible
        if visible:
            self._widget_action.setText("Hide Widget")
        else:
            self._widget_action.setText("Show Widget")

    def show(self) -> None:
        """Show the tray icon."""
        logger.debug("Showing tray icon")
        self._tray.show()

    def hide(self) -> None:
        """Hide the tray icon."""
        logger.debug("Hiding tray icon")
        self._tray.hide()

    def show_message(self, title: str, message: str, duration: int = 3000) -> None:
        """Show a balloon notification."""
        logger.debug("Showing tray message: title=%s, message=%s, duration=%d", title, message, duration)
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, duration)

    def is_visible(self) -> bool:
        """Check if tray icon is visible."""
        return self._tray.isVisible()
