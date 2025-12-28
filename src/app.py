"""Main application class."""

import os
import threading
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from .config import get_settings, STATE_IDLE, STATE_RECORDING, STATE_PROCESSING, STATE_ERROR
from .config import ENGINE_LOCAL, ENGINE_API
from .audio import AudioRecorder, validate_audio
from .recognition import LocalWhisperRecognizer, APIWhisperRecognizer, cleanup_text
from .input import HotkeyManager, inject_text
from .ui import FloatingWidget, TrayIcon, SettingsWindow


class VoiceInputApp(QObject):
    """Main application controller."""

    # Signals for thread-safe UI updates
    state_changed = pyqtSignal(str, str)  # state, message
    audio_level = pyqtSignal(float)
    transcription_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._settings = get_settings()

        # State
        self._state = STATE_IDLE
        self._processing = False

        # Components
        self._recorder = AudioRecorder(self._settings.audio_device)
        self._local_recognizer = LocalWhisperRecognizer(self._settings.model)
        self._api_recognizer = APIWhisperRecognizer(self._settings.openai_api_key)
        self._hotkey_manager = HotkeyManager()

        # UI
        self._widget: FloatingWidget | None = None
        self._tray: TrayIcon | None = None
        self._settings_window: SettingsWindow | None = None

        # Connect signals
        self._connect_signals()

        # Setup
        self._setup_hotkey()
        self._setup_ui()

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.state_changed.connect(self._on_state_changed)
        self.audio_level.connect(self._on_audio_level)
        self.transcription_complete.connect(self._on_transcription_complete)
        self.error_occurred.connect(self._on_error)

        # Audio level callback
        self._recorder.set_level_callback(self._on_audio_level_raw)

    def _setup_hotkey(self) -> None:
        """Setup global hotkey."""
        self._hotkey_manager.set_hotkey(self._settings.hotkey)
        self._hotkey_manager.set_callback(self._on_hotkey_pressed)
        self._hotkey_manager.start()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        # Floating widget with configured size
        self._widget = FloatingWidget(size_key=self._settings.widget_size)
        self._widget.clicked.connect(self.toggle_recording)

        # Restore widget position
        if self._settings.widget_position:
            self._widget.restore_position(self._settings.widget_position)

        # Show/hide based on settings
        if self._settings.show_widget:
            self._widget.show()

        # System tray
        self._tray = TrayIcon()
        self._tray.toggle_recording.connect(self.toggle_recording)
        self._tray.show_widget.connect(self._show_widget)
        self._tray.hide_widget.connect(self._hide_widget)
        self._tray.open_settings.connect(self._open_settings)
        self._tray.quit_app.connect(self.quit)
        self._tray.show()

        # First run message
        if self._settings.first_run:
            self._settings.first_run = False
            QTimer.singleShot(1000, self._show_welcome)

    def _show_welcome(self) -> None:
        """Show welcome message on first run."""
        from .input.hotkey import hotkey_to_string
        hotkey = hotkey_to_string(self._settings.hotkey)
        self._tray.show_message(
            "Whisper Voice Input",
            f"Ready! Press {hotkey} to start recording.\n"
            "Right-click the tray icon for options.",
            5000
        )

    def _on_state_changed(self, state: str, message: str) -> None:
        """Handle state change (UI thread)."""
        self._state = state
        if self._widget:
            self._widget.set_state(state, message)
        if self._tray:
            self._tray.set_state(state)

    def _on_audio_level_raw(self, level: float) -> None:
        """Handle audio level from recorder thread."""
        self.audio_level.emit(level)

    def _on_audio_level(self, level: float) -> None:
        """Handle audio level (UI thread)."""
        if self._widget:
            self._widget.set_audio_level(level)

    def _on_transcription_complete(self, text: str) -> None:
        """Handle completed transcription (UI thread)."""
        self._processing = False
        if text:
            # Inject text
            inject_text(text)
            self.state_changed.emit(STATE_IDLE, "Done!")
            # Brief delay then return to ready
            QTimer.singleShot(1000, lambda: self.state_changed.emit(STATE_IDLE, "Ready"))
        else:
            self.state_changed.emit(STATE_IDLE, "No speech detected")
            QTimer.singleShot(2000, lambda: self.state_changed.emit(STATE_IDLE, "Ready"))

    def _on_error(self, message: str) -> None:
        """Handle error (UI thread)."""
        self._processing = False
        self.state_changed.emit(STATE_ERROR, message)
        # Return to ready after delay
        QTimer.singleShot(3000, lambda: self.state_changed.emit(STATE_IDLE, "Ready"))

    def _on_hotkey_pressed(self) -> None:
        """Handle hotkey press (from hotkey thread)."""
        # Use QTimer to ensure we're on the main thread
        QTimer.singleShot(0, self.toggle_recording)

    def toggle_recording(self) -> None:
        """Toggle recording state."""
        if self._processing:
            return  # Don't interrupt processing

        if self._state == STATE_RECORDING:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        """Start recording audio."""
        if self._recorder.is_recording():
            return

        self.state_changed.emit(STATE_RECORDING, "Recording...")
        self._recorder.start()

    def _stop_recording(self) -> None:
        """Stop recording and process audio."""
        if not self._recorder.is_recording():
            return

        self.state_changed.emit(STATE_PROCESSING, "Processing...")
        self._processing = True

        # Stop recording and get audio file
        audio_path = self._recorder.stop()

        if audio_path is None or not validate_audio(audio_path):
            self.error_occurred.emit("No audio recorded")
            return

        # Process in background thread
        threading.Thread(
            target=self._process_audio,
            args=(audio_path,),
            daemon=True
        ).start()

    def _process_audio(self, audio_path: Path) -> None:
        """Process audio file (runs in background thread)."""
        try:
            # Select recognizer
            if self._settings.engine == ENGINE_API:
                recognizer = self._api_recognizer
                recognizer.set_api_key(self._settings.openai_api_key)
            else:
                recognizer = self._local_recognizer
                recognizer.set_model(self._settings.model)

            # Transcribe
            result = recognizer.transcribe(audio_path, self._settings.language)

            # Clean up temp file
            try:
                os.unlink(audio_path)
            except Exception:
                pass

            if result.success:
                # Clean up text
                text = cleanup_text(result.text)
                self.transcription_complete.emit(text)
            else:
                self.error_occurred.emit(result.error or "Transcription failed")

        except Exception as e:
            self.error_occurred.emit(str(e))

    def _show_widget(self) -> None:
        """Show the floating widget."""
        if self._widget:
            self._widget.show()
            self._settings.show_widget = True
        if self._tray:
            self._tray.set_widget_visible(True)

    def _hide_widget(self) -> None:
        """Hide the floating widget."""
        if self._widget:
            # Save position before hiding
            self._settings.widget_position = self._widget.save_position()
            self._widget.hide()
            self._settings.show_widget = False
        if self._tray:
            self._tray.set_widget_visible(False)

    def _open_settings(self) -> None:
        """Open settings window."""
        if self._settings_window is None:
            self._settings_window = SettingsWindow()
            self._settings_window.settings_changed.connect(self._on_settings_changed)
            self._settings_window.hotkey_changed.connect(self._on_hotkey_changed)
            self._settings_window.widget_size_changed.connect(self._on_widget_size_changed)

        # Ensure window is visible and focused
        self._settings_window.showNormal()
        self._settings_window.raise_()
        self._settings_window.activateWindow()

    def _on_settings_changed(self) -> None:
        """Handle settings change."""
        # Update recorder device
        self._recorder.set_device(self._settings.audio_device)

        # Update recognizer model
        self._local_recognizer.set_model(self._settings.model)

        # Update API key
        self._api_recognizer.set_api_key(self._settings.openai_api_key)

    def _on_hotkey_changed(self, hotkey: dict) -> None:
        """Handle hotkey change."""
        self._hotkey_manager.stop()
        self._hotkey_manager.set_hotkey(hotkey)
        self._hotkey_manager.start()

    def _on_widget_size_changed(self, size_key: str) -> None:
        """Handle widget size change."""
        if self._widget:
            self._widget.set_size(size_key)

    def quit(self) -> None:
        """Quit the application."""
        # Save widget position
        if self._widget and self._widget.isVisible():
            self._settings.widget_position = self._widget.save_position()

        # Stop hotkey listener
        self._hotkey_manager.stop()

        # Cancel any recording
        self._recorder.cancel()

        # Hide UI
        if self._widget:
            self._widget.hide()
        if self._tray:
            self._tray.hide()

        # Quit app
        self._app.quit()

    def run(self) -> int:
        """Run the application."""
        return self._app.exec()
