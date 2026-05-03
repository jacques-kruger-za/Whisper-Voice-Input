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
    QTabWidget,
    QListWidget,
    QSlider,
    QInputDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ..config import get_settings, WHISPER_MODELS, SUPPORTED_LANGUAGES, ENGINE_LOCAL, ENGINE_API, WIDGET_SIZES
from ..config.constants import (
    APP_NAME, APP_VERSION,
    PUNCTUATION_WORDS, COMMAND_DEFINITIONS, COMMAND_WAKE_WORD,
)
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
    command_hotkey_changed = pyqtSignal(dict)
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
        self.setMinimumSize(640, 640)
        self.resize(720, 820)
        self.setStyleSheet(SETTINGS_STYLE)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Tab widget
        tabs = QTabWidget()

        # General settings tab
        tabs.addTab(self._create_general_tab(), "General")

        # Commands & Vocabulary tab
        tabs.addTab(self._create_commands_tab(), "Commands && Vocabulary")

        main_layout.addWidget(tabs)

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
        """Create hotkey configuration section (dictation + command)."""
        group = QGroupBox("Hotkeys")
        layout = QFormLayout(group)

        # Dictation hotkey
        dict_layout = QHBoxLayout()
        self._hotkey_display = QLineEdit()
        self._hotkey_display.setReadOnly(True)
        self._hotkey_display.setPlaceholderText("Press 'Set' to configure")
        dict_layout.addWidget(self._hotkey_display)

        self._hotkey_btn = QPushButton("Set")
        self._hotkey_btn.setFixedWidth(60)
        self._hotkey_btn.clicked.connect(self._capture_hotkey)
        dict_layout.addWidget(self._hotkey_btn)

        layout.addRow("Toggle Dictation:", dict_layout)

        # Command-only hotkey (separate keystroke modality — say a command
        # without the wake-word prefix; the hotkey itself signals intent)
        cmd_layout = QHBoxLayout()
        self._command_hotkey_display = QLineEdit()
        self._command_hotkey_display.setReadOnly(True)
        self._command_hotkey_display.setPlaceholderText("Press 'Set' to configure")
        cmd_layout.addWidget(self._command_hotkey_display)

        self._command_hotkey_btn = QPushButton("Set")
        self._command_hotkey_btn.setFixedWidth(60)
        self._command_hotkey_btn.clicked.connect(self._capture_command_hotkey)
        cmd_layout.addWidget(self._command_hotkey_btn)

        layout.addRow("Toggle Command:", cmd_layout)

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

        # Streaming mode (experimental) — continuous transcription with
        # mid-utterance text injection vs the default record-then-transcribe.
        self._streaming_check = QCheckBox(
            "Streaming mode (experimental — text appears as you speak)"
        )
        layout.addRow("", self._streaming_check)

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

    def _create_general_tab(self) -> QWidget:
        """Create general settings tab."""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
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

        return widget

    def _create_commands_tab(self) -> QWidget:
        """Create commands & vocabulary tab."""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # ── Section 1: Custom Vocabulary (Whisper bias) ────────────────────
        vocab_group = QGroupBox("Custom Vocabulary")
        vocab_layout = QVBoxLayout(vocab_group)

        vocab_desc = QLabel(
            "Proper nouns, names, jargon, or technical terms that Whisper "
            "tends to mishear. These are passed as a hint to bias transcription "
            "(e.g. 'Jacques', 'Anthropic', 'rapidfuzz')."
        )
        vocab_desc.setWordWrap(True)
        vocab_desc.setStyleSheet("color: #888888;")
        vocab_layout.addWidget(vocab_desc)

        list_layout = QHBoxLayout()
        self._vocabulary_list = QListWidget()
        self._vocabulary_list.setMinimumHeight(120)
        list_layout.addWidget(self._vocabulary_list)

        button_layout = QVBoxLayout()
        self._add_vocab_btn = QPushButton("Add")
        self._add_vocab_btn.clicked.connect(self._add_vocabulary_word)
        button_layout.addWidget(self._add_vocab_btn)
        self._remove_vocab_btn = QPushButton("Remove")
        self._remove_vocab_btn.clicked.connect(self._remove_vocabulary_word)
        button_layout.addWidget(self._remove_vocab_btn)
        button_layout.addStretch()
        list_layout.addLayout(button_layout)

        vocab_layout.addLayout(list_layout)
        layout.addWidget(vocab_group)

        # ── Section 2: Text Editing Vocabulary (spoken punctuation) ────────
        editing_group = QGroupBox("Text Editing Vocabulary")
        editing_layout = QVBoxLayout(editing_group)

        editing_desc = QLabel(
            "Spoken words that get converted into characters during dictation. "
            "Works mid-sentence — say 'comma' or 'new line' as you talk. "
            "Built-in entries are marked [default]; your additions show with ★ "
            "and override defaults with the same phrase."
        )
        editing_desc.setWordWrap(True)
        editing_desc.setStyleSheet("color: #888888;")
        editing_layout.addWidget(editing_desc)

        punct_row = QHBoxLayout()
        self._punctuation_list = QListWidget()
        self._punctuation_list.setMinimumHeight(150)
        punct_row.addWidget(self._punctuation_list)

        punct_btns = QVBoxLayout()
        self._add_punct_btn = QPushButton("Add")
        self._add_punct_btn.clicked.connect(self._add_punctuation)
        punct_btns.addWidget(self._add_punct_btn)
        self._remove_punct_btn = QPushButton("Remove")
        self._remove_punct_btn.clicked.connect(self._remove_punctuation)
        punct_btns.addWidget(self._remove_punct_btn)
        punct_btns.addStretch()
        punct_row.addLayout(punct_btns)
        editing_layout.addLayout(punct_row)

        layout.addWidget(editing_group)

        # ── Section 3: Editor Commands (keystroke dispatch) ────────────────
        commands_group = QGroupBox("Editor Commands")
        commands_layout = QVBoxLayout(commands_group)

        commands_desc = QLabel(
            f"Send keystrokes to the focused editor by saying "
            f"<b>'{COMMAND_WAKE_WORD} &lt;name&gt;'</b> "
            f"(e.g. '{COMMAND_WAKE_WORD} save'). The wake-word prefix prevents "
            f"false positives during normal dictation. Built-ins are [default]; "
            f"your additions show ★."
        )
        commands_desc.setWordWrap(True)
        commands_desc.setStyleSheet("color: #888888;")
        commands_layout.addWidget(commands_desc)

        self._commands_enabled_check = QCheckBox("Commands active")
        self._commands_enabled_check.setChecked(True)
        commands_layout.addWidget(self._commands_enabled_check)

        cmd_row = QHBoxLayout()
        self._commands_list = QListWidget()
        self._commands_list.setMinimumHeight(150)
        cmd_row.addWidget(self._commands_list)

        cmd_btns = QVBoxLayout()
        self._add_cmd_btn = QPushButton("Add")
        self._add_cmd_btn.clicked.connect(self._add_command)
        cmd_btns.addWidget(self._add_cmd_btn)
        self._remove_cmd_btn = QPushButton("Remove")
        self._remove_cmd_btn.clicked.connect(self._remove_command)
        cmd_btns.addWidget(self._remove_cmd_btn)
        cmd_btns.addStretch()
        cmd_row.addLayout(cmd_btns)
        commands_layout.addLayout(cmd_row)

        layout.addWidget(commands_group)

        # Hidden: threshold slider kept for backward compat with save/load,
        # not exposed in UI now that wake-word eliminates ambiguity.
        self._threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self._threshold_slider.setMinimum(70)
        self._threshold_slider.setMaximum(90)
        self._threshold_slider.setValue(80)
        self._threshold_slider.hide()
        self._threshold_value_label = QLabel("80")
        self._threshold_value_label.hide()

        layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        return widget

    def _load_settings(self) -> None:
        """Load current settings into UI."""
        # Hotkey (dictation)
        hotkey = self._settings.hotkey
        self._hotkey_display.setText(hotkey_to_string(hotkey))
        self._current_hotkey = hotkey.copy()

        # Hotkey (command)
        cmd_hotkey = getattr(self._settings, 'command_hotkey', None)
        if cmd_hotkey:
            self._command_hotkey_display.setText(hotkey_to_string(cmd_hotkey))
            self._current_command_hotkey = dict(cmd_hotkey)
        else:
            self._current_command_hotkey = {}

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

        # Custom vocabulary
        vocabulary = getattr(self._settings, 'custom_vocabulary', [])
        self._vocabulary_list.clear()
        for word in vocabulary:
            self._vocabulary_list.addItem(word)

        # Command threshold
        threshold = getattr(self._settings, 'command_threshold', 80)
        self._threshold_slider.setValue(int(threshold))

        # Commands active
        commands_enabled = getattr(self._settings, 'commands_enabled', True)
        self._commands_enabled_check.setChecked(bool(commands_enabled))

        # Streaming mode (experimental)
        streaming = getattr(self._settings, 'streaming_mode', False)
        self._streaming_check.setChecked(bool(streaming))

        # Custom punctuation + commands (working copies — modified by buttons,
        # persisted on Save)
        self._punct_customs = dict(getattr(self._settings, 'custom_punctuation', {}) or {})
        self._cmd_customs = dict(getattr(self._settings, 'custom_commands', {}) or {})
        self._refresh_punctuation_list()
        self._refresh_commands_list()

        # Update UI state
        self._on_engine_changed()

    def _on_engine_changed(self) -> None:
        """Handle engine selection change."""
        engine = self._engine_combo.currentData()
        is_local = engine == ENGINE_LOCAL

        # Show/hide relevant options
        self._model_combo.setEnabled(is_local)
        self._api_key_edit.setEnabled(not is_local)

    def _on_threshold_changed(self, value: int) -> None:
        """Handle threshold slider change."""
        self._threshold_value_label.setText(str(value))

    def _add_vocabulary_word(self) -> None:
        """Add a new word to custom vocabulary."""
        word, ok = QInputDialog.getText(
            self,
            "Add Vocabulary Word",
            "Enter a word or phrase:",
        )

        if ok and word.strip():
            word = word.strip()
            # Check for duplicates
            items = [self._vocabulary_list.item(i).text() for i in range(self._vocabulary_list.count())]
            if word not in items:
                self._vocabulary_list.addItem(word)
            else:
                QMessageBox.information(
                    self,
                    "Duplicate Word",
                    f"'{word}' is already in the vocabulary list.",
                )

    def _remove_vocabulary_word(self) -> None:
        """Remove selected word from custom vocabulary."""
        current_item = self._vocabulary_list.currentItem()
        if current_item:
            self._vocabulary_list.takeItem(self._vocabulary_list.row(current_item))

    # ── Spoken-punctuation list management ────────────────────────────────

    def _refresh_punctuation_list(self) -> None:
        """Rebuild the punctuation list from defaults + working customs."""
        self._punctuation_list.clear()
        # Defaults first (stable order from constants), then customs
        for phrase, symbol in PUNCTUATION_WORDS.items():
            display = symbol.replace("\n", "↵").replace("\t", "→ ")
            item = self._punctuation_list.addItem(f"  {phrase}  ⇒  {display}    [default]")
        for phrase, symbol in self._punct_customs.items():
            display = symbol.replace("\n", "↵").replace("\t", "→ ")
            self._punctuation_list.addItem(f"  ★ {phrase}  ⇒  {display}")

    def _add_punctuation(self) -> None:
        phrase, ok = QInputDialog.getText(
            self, "Add Spoken Punctuation",
            "Spoken phrase (e.g. 'open paren'):",
        )
        if not ok or not phrase.strip():
            return
        phrase = phrase.strip().lower()

        symbol, ok = QInputDialog.getText(
            self, "Add Spoken Punctuation",
            f"Replacement for '{phrase}'\n"
            f"(use \\n for newline, \\t for tab):",
        )
        if not ok:
            return
        symbol = symbol.replace("\\n", "\n").replace("\\t", "\t")
        if not symbol:
            return
        self._punct_customs[phrase] = symbol
        self._refresh_punctuation_list()

    def _remove_punctuation(self) -> None:
        item = self._punctuation_list.currentItem()
        if not item:
            return
        text = item.text()
        if "[default]" in text:
            QMessageBox.information(
                self, "Built-in entry",
                "Default entries cannot be removed. Add a custom entry with the "
                "same phrase to override it.",
            )
            return
        # Custom entry — extract phrase between "★ " and "  ⇒"
        if "★" in text:
            phrase_part = text.split("★", 1)[1].split("⇒", 1)[0].strip()
            if phrase_part in self._punct_customs:
                del self._punct_customs[phrase_part]
                self._refresh_punctuation_list()

    # ── Editor-command list management ────────────────────────────────────

    def _refresh_commands_list(self) -> None:
        """Rebuild the commands list from defaults + working customs."""
        self._commands_list.clear()
        for phrase, info in COMMAND_DEFINITIONS.items():
            self._commands_list.addItem(
                f"  {COMMAND_WAKE_WORD} {phrase}  ⇒  {info['keystroke']}    [default]"
            )
        for phrase, keystroke in self._cmd_customs.items():
            self._commands_list.addItem(
                f"  ★ {COMMAND_WAKE_WORD} {phrase}  ⇒  {keystroke}"
            )

    def _add_command(self) -> None:
        phrase, ok = QInputDialog.getText(
            self, "Add Editor Command",
            "Spoken phrase (after '" + COMMAND_WAKE_WORD + "'):",
        )
        if not ok or not phrase.strip():
            return
        phrase = phrase.strip().lower()

        keystroke, ok = QInputDialog.getText(
            self, "Add Editor Command",
            f"Keystroke for '{COMMAND_WAKE_WORD} {phrase}'\n"
            f"(e.g. ctrl+s, ctrl+shift+f, alt+tab):",
        )
        if not ok or not keystroke.strip():
            return
        self._cmd_customs[phrase] = keystroke.strip().lower()
        self._refresh_commands_list()

    def _remove_command(self) -> None:
        item = self._commands_list.currentItem()
        if not item:
            return
        text = item.text()
        if "[default]" in text:
            QMessageBox.information(
                self, "Built-in command",
                "Default commands cannot be removed. Add a custom command with the "
                "same phrase to override the keystroke.",
            )
            return
        if "★" in text:
            # Format: "  ★ command <phrase>  ⇒  <keystroke>"
            after_star = text.split("★", 1)[1].strip()  # "command <phrase>  ⇒  <keystroke>"
            if after_star.lower().startswith(COMMAND_WAKE_WORD + " "):
                rest = after_star[len(COMMAND_WAKE_WORD) + 1:]
                phrase_part = rest.split("⇒", 1)[0].strip()
                if phrase_part in self._cmd_customs:
                    del self._cmd_customs[phrase_part]
                    self._refresh_commands_list()

    def _capture_hotkey(self) -> None:
        """Start capturing a new dictation hotkey."""
        self._hotkey_btn.setText("...")
        self._hotkey_btn.setEnabled(False)
        self._hotkey_display.setText("Press your hotkey...")

        self._hotkey_capture = HotkeyCapture()
        self._hotkey_capture.capture(self._on_hotkey_captured)

    def _on_hotkey_captured(self, hotkey: dict) -> None:
        """Handle captured dictation hotkey."""
        self._current_hotkey = hotkey
        self._hotkey_display.setText(hotkey_to_string(hotkey))
        self._hotkey_btn.setText("Set")
        self._hotkey_btn.setEnabled(True)

    def _capture_command_hotkey(self) -> None:
        """Start capturing a new command hotkey."""
        self._command_hotkey_btn.setText("...")
        self._command_hotkey_btn.setEnabled(False)
        self._command_hotkey_display.setText("Press your hotkey...")

        self._command_hotkey_capture = HotkeyCapture()
        self._command_hotkey_capture.capture(self._on_command_hotkey_captured)

    def _on_command_hotkey_captured(self, hotkey: dict) -> None:
        """Handle captured command hotkey."""
        self._current_command_hotkey = hotkey
        self._command_hotkey_display.setText(hotkey_to_string(hotkey))
        self._command_hotkey_btn.setText("Set")
        self._command_hotkey_btn.setEnabled(True)

    def _save_settings(self) -> None:
        """Save settings and close."""
        # Hotkey
        old_hotkey = self._settings.hotkey
        self._settings.hotkey = self._current_hotkey

        old_command_hotkey = getattr(self._settings, 'command_hotkey', {})
        if hasattr(self._settings, 'command_hotkey') and self._current_command_hotkey:
            self._settings.command_hotkey = self._current_command_hotkey

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

        # Custom vocabulary
        vocabulary = [self._vocabulary_list.item(i).text() for i in range(self._vocabulary_list.count())]
        if hasattr(self._settings, 'custom_vocabulary'):
            self._settings.custom_vocabulary = vocabulary

        # Command threshold
        threshold = self._threshold_slider.value()
        if hasattr(self._settings, 'command_threshold'):
            self._settings.command_threshold = threshold

        # Commands active
        if hasattr(self._settings, 'commands_enabled'):
            self._settings.commands_enabled = self._commands_enabled_check.isChecked()

        # Streaming mode (experimental)
        if hasattr(self._settings, 'streaming_mode'):
            self._settings.streaming_mode = self._streaming_check.isChecked()

        # Custom punctuation + commands
        if hasattr(self._settings, 'custom_punctuation'):
            self._settings.custom_punctuation = self._punct_customs
        if hasattr(self._settings, 'custom_commands'):
            self._settings.custom_commands = self._cmd_customs

        # Handle autostart
        self._update_autostart()

        # Notify of changes
        self.settings_changed.emit()
        if self._current_hotkey != old_hotkey:
            self.hotkey_changed.emit(self._current_hotkey)
        if self._current_command_hotkey and self._current_command_hotkey != old_command_hotkey:
            self.command_hotkey_changed.emit(self._current_command_hotkey)
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
