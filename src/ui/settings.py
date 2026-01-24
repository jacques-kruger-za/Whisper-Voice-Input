"""Settings window."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QFormLayout,
    QWidget,
    QScrollArea,
    QFrame,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ..config import get_settings, WHISPER_MODELS, SUPPORTED_LANGUAGES, ENGINE_LOCAL, ENGINE_API, WIDGET_SIZES
from ..config.constants import APP_NAME, APP_VERSION
from ..audio import AudioRecorder
from ..input.hotkey import HotkeyCapture, hotkey_to_string
from ..config.logging_config import get_logger
from .styles import SETTINGS_STYLE

logger = get_logger(__name__)


class SettingsWindow(QDialog):
    """Application settings window."""

    # Signals
    settings_changed = pyqtSignal()
    hotkey_changed = pyqtSignal(dict)
    widget_size_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = get_settings()
        self._hotkey_capture: HotkeyCapture | None = None
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Initialize the settings UI."""
        self.setWindowTitle(f"{APP_NAME} Settings")
        self.setMinimumSize(450, 500)
        self.setStyleSheet(SETTINGS_STYLE)

        # Main layout with scroll area
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Hotkey section
        layout.addWidget(self._create_hotkey_section())

        # Audio section
        layout.addWidget(self._create_audio_section())

        # Appearance section
        layout.addWidget(self._create_appearance_section())

        # Recognition section
        layout.addWidget(self._create_recognition_section())

        # Startup section
        layout.addWidget(self._create_startup_section())

        # About section
        layout.addWidget(self._create_about_section())

        layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(20, 10, 20, 20)

        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self._save_settings)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self._cancel_btn)
        button_layout.addWidget(self._save_btn)

        main_layout.addLayout(button_layout)

    def _create_hotkey_section(self) -> QGroupBox:
        """Create hotkey configuration section."""
        group = QGroupBox("Hotkey")
        layout = QFormLayout(group)

        # Current hotkey display
        hotkey_layout = QHBoxLayout()
        self._hotkey_display = QLineEdit()
        self._hotkey_display.setReadOnly(True)
        self._hotkey_display.setPlaceholderText("Press 'Set' to configure")
        hotkey_layout.addWidget(self._hotkey_display)

        self._hotkey_btn = QPushButton("Set")
        self._hotkey_btn.setFixedWidth(60)
        self._hotkey_btn.clicked.connect(self._capture_hotkey)
        hotkey_layout.addWidget(self._hotkey_btn)

        layout.addRow("Toggle Recording:", hotkey_layout)

        return group

    def _create_audio_section(self) -> QGroupBox:
        """Create audio configuration section."""
        group = QGroupBox("Audio")
        layout = QFormLayout(group)

        # Input device selection
        self._device_combo = QComboBox()
        self._device_combo.addItem("System Default", None)
        for device in AudioRecorder.get_devices():
            self._device_combo.addItem(device["name"], device["name"])
        layout.addRow("Input Device:", self._device_combo)

        return group

    def _create_appearance_section(self) -> QGroupBox:
        """Create appearance configuration section."""
        group = QGroupBox("Appearance")
        layout = QFormLayout(group)

        # Widget size selection
        self._widget_size_combo = QComboBox()
        size_labels = {
            "compact": "Compact (60px)",
            "medium": "Medium (80px)",
            "large": "Large (100px)",
        }
        for key in WIDGET_SIZES:
            self._widget_size_combo.addItem(size_labels.get(key, key), key)
        layout.addRow("Widget Size:", self._widget_size_combo)

        return group

    def _create_recognition_section(self) -> QGroupBox:
        """Create recognition configuration section."""
        group = QGroupBox("Recognition")
        layout = QFormLayout(group)

        # Engine selection
        self._engine_combo = QComboBox()
        self._engine_combo.addItem("Local (Faster-Whisper)", ENGINE_LOCAL)
        self._engine_combo.addItem("OpenAI API", ENGINE_API)
        self._engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        layout.addRow("Engine:", self._engine_combo)

        # Model selection (for local)
        self._model_combo = QComboBox()
        for model in WHISPER_MODELS:
            label = model
            if model == "base":
                label += " (Recommended)"
            elif model == "tiny":
                label += " (Fastest)"
            elif model == "large-v3":
                label += " (Best quality)"
            self._model_combo.addItem(label, model)
        layout.addRow("Model:", self._model_combo)

        # Language selection
        self._language_combo = QComboBox()
        for code, name in SUPPORTED_LANGUAGES.items():
            self._language_combo.addItem(name, code)
        layout.addRow("Language:", self._language_combo)

        # API Key (for OpenAI)
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText("sk-...")
        layout.addRow("OpenAI API Key:", self._api_key_edit)

        return group

    def _create_startup_section(self) -> QGroupBox:
        """Create startup configuration section."""
        group = QGroupBox("Startup")
        layout = QVBoxLayout(group)

        self._autostart_check = QCheckBox("Start with Windows")
        layout.addWidget(self._autostart_check)

        self._show_widget_check = QCheckBox("Show widget on startup")
        layout.addWidget(self._show_widget_check)

        return group

    def _create_about_section(self) -> QGroupBox:
        """Create about section."""
        group = QGroupBox("About")
        layout = QVBoxLayout(group)

        name_label = QLabel(f"<b>{APP_NAME}</b>")
        layout.addWidget(name_label)

        version_label = QLabel(f"Version {APP_VERSION}")
        layout.addWidget(version_label)

        desc_label = QLabel("Universal voice input for Windows")
        desc_label.setStyleSheet("color: #888888;")
        layout.addWidget(desc_label)

        return group

    def _load_settings(self) -> None:
        """Load current settings into UI."""
        # Hotkey
        hotkey = self._settings.hotkey
        self._hotkey_display.setText(hotkey_to_string(hotkey))
        self._current_hotkey = hotkey.copy()

        # Audio device
        device = self._settings.audio_device
        for i in range(self._device_combo.count()):
            if self._device_combo.itemData(i) == device:
                self._device_combo.setCurrentIndex(i)
                break

        # Engine
        engine = self._settings.engine
        for i in range(self._engine_combo.count()):
            if self._engine_combo.itemData(i) == engine:
                self._engine_combo.setCurrentIndex(i)
                break

        # Model
        model = self._settings.model
        for i in range(self._model_combo.count()):
            if self._model_combo.itemData(i) == model:
                self._model_combo.setCurrentIndex(i)
                break

        # Language
        language = self._settings.language
        for i in range(self._language_combo.count()):
            if self._language_combo.itemData(i) == language:
                self._language_combo.setCurrentIndex(i)
                break

        # API key
        self._api_key_edit.setText(self._settings.openai_api_key)

        # Startup
        self._autostart_check.setChecked(self._settings.start_with_windows)
        self._show_widget_check.setChecked(self._settings.show_widget)

        # Appearance
        widget_size = self._settings.widget_size
        for i in range(self._widget_size_combo.count()):
            if self._widget_size_combo.itemData(i) == widget_size:
                self._widget_size_combo.setCurrentIndex(i)
                break

        # Update UI state
        self._on_engine_changed()

    def _on_engine_changed(self) -> None:
        """Handle engine selection change."""
        engine = self._engine_combo.currentData()
        is_local = engine == ENGINE_LOCAL

        # Show/hide relevant options
        self._model_combo.setEnabled(is_local)
        self._api_key_edit.setEnabled(not is_local)

    def _capture_hotkey(self) -> None:
        """Start capturing a new hotkey."""
        self._hotkey_btn.setText("...")
        self._hotkey_btn.setEnabled(False)
        self._hotkey_display.setText("Press your hotkey...")

        self._hotkey_capture = HotkeyCapture()
        self._hotkey_capture.capture(self._on_hotkey_captured)

    def _on_hotkey_captured(self, hotkey: dict) -> None:
        """Handle captured hotkey."""
        self._current_hotkey = hotkey
        self._hotkey_display.setText(hotkey_to_string(hotkey))
        self._hotkey_btn.setText("Set")
        self._hotkey_btn.setEnabled(True)

    def _save_settings(self) -> None:
        """Save settings and close."""
        # Hotkey
        old_hotkey = self._settings.hotkey
        self._settings.hotkey = self._current_hotkey

        # Audio
        self._settings.audio_device = self._device_combo.currentData()

        # Recognition
        self._settings.engine = self._engine_combo.currentData()
        self._settings.model = self._model_combo.currentData()
        self._settings.language = self._language_combo.currentData()
        self._settings.openai_api_key = self._api_key_edit.text()

        # Startup
        self._settings.start_with_windows = self._autostart_check.isChecked()
        self._settings.show_widget = self._show_widget_check.isChecked()

        # Appearance
        old_widget_size = self._settings.widget_size
        new_widget_size = self._widget_size_combo.currentData()
        self._settings.widget_size = new_widget_size

        # Handle autostart
        self._update_autostart()

        # Notify of changes
        self.settings_changed.emit()
        if self._current_hotkey != old_hotkey:
            self.hotkey_changed.emit(self._current_hotkey)
        if new_widget_size != old_widget_size:
            self.widget_size_changed.emit(new_widget_size)

        self.accept()

    def _update_autostart(self) -> None:
        """Update Windows autostart setting."""
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = APP_NAME.replace(" ", "")

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                key_path,
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
            )

            if self._settings.start_with_windows:
                import sys
                exe_path = sys.executable
                script_path = sys.argv[0] if sys.argv else ""
                if script_path:
                    value = f'"{exe_path}" "{script_path}"'
                else:
                    value = f'"{exe_path}"'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, value)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass

            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to update autostart: {e}")

    def closeEvent(self, event) -> None:
        """Handle window close."""
        if self._hotkey_capture:
            self._hotkey_capture.cancel()
        super().closeEvent(event)
