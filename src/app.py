"""Main application class."""

import os
import sys
import threading
from pathlib import Path

import pyperclip
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QTimerEvent, QPoint

from .config import get_settings, STATE_IDLE, STATE_RECORDING, STATE_PROCESSING, STATE_ERROR
from .config import ENGINE_LOCAL, ENGINE_API
from .config.constants import (
    TRANSCRIPTION_TIMEOUT_SECONDS,
    STREAM_WINDOW_SECONDS, STREAM_INTERVAL_SECONDS,
    STREAM_VAD_MIN_SILENCE_MS, STREAM_FOCUS_SETTLE_MS,
    STATE_COMMAND,
    STREAM_AUTO_PAUSE_SECONDS, STREAM_AUTO_STOP_SECONDS,
    COMMAND_AUTO_STOP_AFTER_SPEECH_SECONDS, COMMAND_NO_SPEECH_TIMEOUT_SECONDS,
    SILENCE_POLL_INTERVAL_MS,
)
from .config.logging_config import get_logger
from .audio import AudioRecorder, validate_audio, SilenceMonitor
from .recognition import (
    LocalWhisperRecognizer, APIWhisperRecognizer, cleanup_text,
    CommandProcessor, classify_transcription,
    StreamingTranscriber,
)
from .config.constants import SAMPLE_RATE
from .input import HotkeyManager, inject_text
from .input.window_focus import (
    save_foreground_window, restore_foreground_window,
    is_window_valid, get_foreground_window_if_external, get_window_title,
)
from .ui import FloatingWidget, TrayIcon, SettingsWindow
from .ui.callout import TranscriptionCallout

# Module logger
logger = get_logger("app")


class VoiceInputApp(QObject):
    """Main application controller."""

    # Signals for thread-safe UI updates
    state_changed = pyqtSignal(str, str)  # state, message
    audio_level = pyqtSignal(float)
    transcription_complete = pyqtSignal(str)
    transcription_segment = pyqtSignal(str)  # per-segment streaming
    command_detected = pyqtSignal(object)  # CommandResult from background thread
    error_occurred = pyqtSignal(str)
    # Streaming-mode signals (worker thread → UI thread)
    streaming_committed = pyqtSignal(str)
    streaming_tentative = pyqtSignal(str)
    _hotkey_signal = pyqtSignal(object)  # HWND from hotkey thread → main thread
    _command_hotkey_signal = pyqtSignal(object)  # HWND from command hotkey thread

    def __init__(self, app: QApplication):
        super().__init__()
        logger.info("Initializing VoiceInputApp")
        self._app = app
        self._settings = get_settings()

        # State
        self._state = STATE_IDLE
        self._processing = False
        self._error_recovery_timer_id: int | None = None
        self._transcription_thread: threading.Thread | None = None
        self._saved_hwnd: int | None = None  # Foreground window to restore after transcription
        self._last_external_hwnd: int | None = None  # Last non-self foreground window (polled)
        self._timeout_timer = QTimer()
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._check_transcription_timeout)
        logger.debug("Initial state: %s", STATE_IDLE)

        # Components
        logger.debug("Creating audio recorder with device: %s", self._settings.audio_device)
        self._recorder = AudioRecorder(self._settings.audio_device)
        logger.debug("Creating local recognizer with model: %s", self._settings.model)
        self._local_recognizer = LocalWhisperRecognizer(self._settings.model)
        # Separate recognizer for streaming. Holds its own (typically smaller)
        # model loaded into memory. Lets users keep 'small' for batch quality
        # and 'base' for streaming speed without paying re-load cost on every
        # mode switch.
        logger.debug("Creating streaming recognizer with model: %s", self._settings.streaming_model)
        self._streaming_recognizer = LocalWhisperRecognizer(self._settings.streaming_model)
        logger.debug("Creating API recognizer")
        self._api_recognizer = APIWhisperRecognizer(self._settings.openai_api_key)
        logger.debug("Creating command processor")
        self._command_processor = CommandProcessor()
        self._hotkey_manager = HotkeyManager()
        # Separate listener for the command-only capture hotkey
        self._command_hotkey_manager = HotkeyManager()
        # Tracks whether the recorder is currently capturing for a command
        # (vs dictation). Mutually exclusive with dictation recording.
        self._command_capturing = False

        # Streaming-mode state (None when not active)
        self._streamer: StreamingTranscriber | None = None
        # Whether anything has been injected during the current streaming
        # session — drives leading-space behaviour between committed deltas.
        self._streaming_injected_any = False

        # VAD-driven session lifecycle: shared monitor (only one modality is
        # active at a time), polled by a Qt timer to drive auto-pause/auto-stop.
        self._silence_monitor = SilenceMonitor()
        self._silence_poll_timer = QTimer(self)
        self._silence_poll_timer.timeout.connect(self._poll_silence)

        # UI
        self._widget: FloatingWidget | None = None
        self._tray: TrayIcon | None = None
        self._settings_window: SettingsWindow | None = None

        # Connect signals
        self._connect_signals()

        # Setup
        self._setup_hotkey()
        self._setup_ui()
        logger.info("VoiceInputApp initialization complete")

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        logger.debug("Connecting internal signals")
        self.state_changed.connect(self._on_state_changed)
        self.audio_level.connect(self._on_audio_level)
        self.transcription_complete.connect(self._on_transcription_complete)
        self.transcription_segment.connect(self._on_segment)
        self.command_detected.connect(self._on_command_detected)
        self.streaming_committed.connect(self._on_streaming_committed)
        self.streaming_tentative.connect(self._on_streaming_tentative)
        self.error_occurred.connect(self._on_error)
        self._hotkey_signal.connect(self._toggle_with_focus)
        self._command_hotkey_signal.connect(self._toggle_command_capture)

        # Audio level callback
        self._recorder.set_level_callback(self._on_audio_level_raw)

    def _setup_hotkey(self) -> None:
        """Setup both global hotkeys (dictation + command)."""
        logger.debug("Setting up dictation hotkey: %s", self._settings.hotkey)
        self._hotkey_manager.set_hotkey(self._settings.hotkey)
        self._hotkey_manager.set_callback(self._on_hotkey_pressed)
        self._hotkey_manager.start()

        logger.debug("Setting up command hotkey: %s", self._settings.command_hotkey)
        self._command_hotkey_manager.set_hotkey(self._settings.command_hotkey)
        self._command_hotkey_manager.set_callback(self._on_command_hotkey_pressed)
        self._command_hotkey_manager.start()

        logger.info("Hotkey listeners started (dictation + command)")

    def _setup_ui(self) -> None:
        """Setup UI components."""
        logger.debug("Setting up UI components")

        # Transcription callout popup
        self._callout = TranscriptionCallout()

        # Floating widget with configured size
        logger.debug("Creating floating widget with size: %s", self._settings.widget_size)
        self._widget = FloatingWidget(size_key=self._settings.widget_size)
        self._widget.clicked.connect(self._on_widget_clicked)

        # Restore widget position
        if self._settings.widget_position:
            logger.debug("Restoring widget position: %s", self._settings.widget_position)
            self._widget.restore_position(self._settings.widget_position)

        # Show/hide based on settings
        if self._settings.show_widget:
            self._widget.show()
            logger.debug("Widget shown")

        # System tray
        logger.debug("Creating system tray icon")
        self._tray = TrayIcon()
        self._tray.toggle_recording.connect(self._on_tray_toggle)
        self._tray.show_widget.connect(self._show_widget)
        self._tray.hide_widget.connect(self._hide_widget)
        self._tray.open_settings.connect(self._open_settings)
        self._tray.reset_state.connect(self._reset_state)
        self._tray.restart_app.connect(self._restart_app)
        self._tray.quit_app.connect(self.quit)
        self._tray.show()
        logger.info("UI components initialized")

        # Focus tracker — polls foreground window every 250ms, ignoring our own windows.
        # Gives widget/tray clicks a correct "last external HWND" since clicking
        # our own UI makes it foreground before the click handler runs.
        self._focus_tracker = QTimer()
        self._focus_tracker.timeout.connect(self._track_foreground_window)
        self._focus_tracker.start(250)

        # First run message
        if self._settings.first_run:
            logger.info("First run detected, showing welcome message")
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
        logger.info("State changed: %s -> %s (message: %s)", self._state, state, message)
        self._state = state
        if self._widget:
            self._widget.set_state(state, message)
        if self._tray:
            self._tray.set_state(state)

    def _on_audio_level_raw(self, level: float) -> None:
        """Handle audio level from recorder thread.

        Two consumers: the audio_level Qt signal (drives the bar strip on the
        UI thread) and the SilenceMonitor (drives VAD-based session lifecycle).
        Both are cheap; SilenceMonitor.update is a single threshold compare.
        """
        self._silence_monitor.update(level)
        self.audio_level.emit(level)

    def _on_audio_level(self, level: float) -> None:
        """Handle audio level (UI thread)."""
        if self._widget:
            self._widget.set_audio_level(level)

    def _on_transcription_complete(self, text: str) -> None:
        """Handle completed transcription (UI thread).

        1. Show final text in callout
        2. Restore focus to saved window
        3. Inject text via clipboard paste (after brief delay for focus to settle)
        4. If focus restore failed, show paste-manually warning
        """
        self._timeout_timer.stop()
        self._processing = False
        if text:
            logger.info("Transcription complete: %d characters", len(text))

            # Show final cleaned text in callout
            self._callout.set_final_text(text)

            # Copy text to clipboard first (available for manual paste as fallback)
            pyperclip.copy(text)

            # Try to restore focus and inject
            hwnd = self._saved_hwnd
            self._saved_hwnd = None
            focus_restored = False

            if hwnd and is_window_valid(hwnd):
                focus_restored = restore_foreground_window(hwnd)
            else:
                logger.info("No valid HWND to restore (hwnd=%s)", hwnd)

            if focus_restored:
                # Use QTimer for the delay so we don't block the UI thread
                QTimer.singleShot(150, lambda: self._inject_after_focus(text))
            else:
                # Can't paste automatically — warn user
                logger.info("Auto-paste unavailable, text copied to clipboard")
                self._callout.show_paste_warning(text)
                self.state_changed.emit(STATE_IDLE, "Copied — paste manually")
                if self._tray:
                    self._tray.show_message(
                        "Whisper Voice Input",
                        "Text copied to clipboard. Paste manually with Ctrl+V.",
                        4000
                    )
                QTimer.singleShot(2000, lambda: self.state_changed.emit(STATE_IDLE, "Ready"))
        else:
            logger.info("Transcription complete: no speech detected")
            self._callout.clear()
            self._saved_hwnd = None
            self.state_changed.emit(STATE_IDLE, "No speech detected")
            QTimer.singleShot(2000, lambda: self.state_changed.emit(STATE_IDLE, "Ready"))

    def _inject_after_focus(self, text: str) -> None:
        """Inject text after focus has settled (UI thread, called via QTimer)."""
        logger.info("Injecting text into focused window")
        inject_text(text)
        self.state_changed.emit(STATE_IDLE, "Done!")
        QTimer.singleShot(1500, lambda: self.state_changed.emit(STATE_IDLE, "Ready"))

    def _on_command_detected(self, cmd_result) -> None:
        """Handle voice command (UI thread). Restore focus then execute."""
        self._timeout_timer.stop()
        self._processing = False

        # Reject commands with no keystroke (wake-word matched, no command suffix)
        if not cmd_result.keystroke:
            logger.info("Unknown command: %s", cmd_result.command_phrase)
            self._callout.set_final_text(f"⚡ Unknown: {cmd_result.command_phrase}")
            self._saved_hwnd = None
            self.state_changed.emit(STATE_IDLE, f"Unknown command")
            QTimer.singleShot(2000, lambda: self.state_changed.emit(STATE_IDLE, "Ready"))
            return

        # Show what was detected in the callout
        self._callout.set_final_text(f"⚡ {cmd_result.command_phrase} → {cmd_result.keystroke}")

        hwnd = self._saved_hwnd
        self._saved_hwnd = None

        if hwnd and is_window_valid(hwnd):
            restore_foreground_window(hwnd)
            QTimer.singleShot(150, lambda: self._execute_command_after_focus(cmd_result))
        else:
            logger.warning("Cannot execute command: no valid focus target (hwnd=%s)", hwnd)
            self.state_changed.emit(STATE_IDLE, "Command failed — focus lost")
            QTimer.singleShot(2000, lambda: self.state_changed.emit(STATE_IDLE, "Ready"))

    def _execute_command_after_focus(self, cmd_result) -> None:
        """Execute command after focus settles (UI thread, called via QTimer)."""
        ok = self._command_processor.execute_command(cmd_result)
        msg = f"Done! ({cmd_result.command_phrase})" if ok else "Command failed"
        self.state_changed.emit(STATE_IDLE, msg)
        QTimer.singleShot(1500, lambda: self.state_changed.emit(STATE_IDLE, "Ready"))

    # ── Streaming pipeline (UI thread, fed by Qt signals from worker) ────

    def _on_streaming_committed(self, raw_text: str) -> None:
        """A new committed dictation delta arrived from the streamer.

        Streaming is PURE DICTATION — commands have their own hotkey and
        flow (see _on_command_hotkey). The classify-per-delta logic from
        earlier S3 was removed because it created lifecycle hazards
        (command nulled _saved_hwnd → subsequent dictation discarded).
        """
        if not raw_text or not raw_text.strip():
            return

        cleaned = cleanup_text(raw_text)
        if not cleaned:
            return

        # First commit needs an explicit focus restore + settle delay.
        # Subsequent commits paste immediately into the still-focused target.
        # Set _streaming_injected_any synchronously (BEFORE the QTimer fires)
        # so a second commit arriving inside the settle window doesn't
        # double-restore focus and double-inject (regression of e576c01).
        if not self._streaming_injected_any:
            hwnd = self._saved_hwnd
            if hwnd and is_window_valid(hwnd):
                restore_foreground_window(hwnd)
                self._streaming_injected_any = True  # set before timer fires
                QTimer.singleShot(
                    STREAM_FOCUS_SETTLE_MS,
                    lambda t=cleaned: self._inject_streaming_chunk(t),
                )
                return
            else:
                # No valid target: log once, then absorb future deltas as
                # subsequent-chunks (which will at least try to paste into
                # whatever is currently foreground, even if it's not the
                # original target).
                logger.warning("Streaming: no valid focus target on first delta")
                self._streaming_injected_any = True
                # fall through to subsequent-chunks path

        # Subsequent chunks: paste immediately, prepend a space so words
        # don't smash together across deltas.
        self._inject_streaming_chunk(" " + cleaned)

    def _inject_streaming_chunk(self, text: str) -> None:
        """Paste a streaming chunk via clipboard. Marks session as injected."""
        if not text:
            return
        logger.info("Streaming inject: %r", text[:60])
        inject_text(text)
        self._streaming_injected_any = True

    # ── VAD-driven lifecycle (shared poll handler) ────────────────────────

    def _poll_silence(self) -> None:
        """Tick handler for silence-driven transitions (UI thread).

        Routes to the appropriate per-modality logic based on what's active.
        Runs every SILENCE_POLL_INTERVAL_MS while a session is live.
        """
        if self._command_capturing:
            self._poll_silence_command()
        elif self._streamer is not None:
            self._poll_silence_streaming()

    def _poll_silence_streaming(self) -> None:
        """Auto-pause / auto-stop transitions for streaming dictation.

        - Continuous silence ≥ STREAM_AUTO_STOP_SECONDS: end the session.
        - Continuous silence ≥ STREAM_AUTO_PAUSE_SECONDS: pause Whisper rounds
          (audio still buffers; resume on next loud sample).
        - Otherwise: ensure we're resumed.
        """
        silence = self._silence_monitor.silence_duration()
        if silence >= STREAM_AUTO_STOP_SECONDS:
            logger.info("Streaming auto-stop after %.1fs silence", silence)
            self._stop_streaming()
            return
        if silence >= STREAM_AUTO_PAUSE_SECONDS:
            if self._streamer and not self._streamer.is_paused:
                self._streamer.pause()
        else:
            if self._streamer and self._streamer.is_paused:
                self._streamer.resume()

    def _poll_silence_command(self) -> None:
        """Auto-fire / auto-cancel transitions for command capture.

        - Speech detected, then silence ≥ COMMAND_AUTO_STOP_AFTER_SPEECH:
          fire (run the existing _stop_command_capture path → transcribe → keystroke).
        - No speech ever, elapsed ≥ COMMAND_NO_SPEECH_TIMEOUT: cancel.
        """
        if self._silence_monitor.speech_detected():
            silence = self._silence_monitor.silence_duration()
            if silence >= COMMAND_AUTO_STOP_AFTER_SPEECH_SECONDS:
                logger.info("Command auto-fire after %.2fs silence post-speech", silence)
                self._stop_command_capture()
        else:
            elapsed = self._silence_monitor.elapsed_since_start()
            if elapsed >= COMMAND_NO_SPEECH_TIMEOUT_SECONDS:
                logger.info("Command auto-cancel: no speech in %.1fs", elapsed)
                self._cancel_command_capture()

    def _cancel_command_capture(self) -> None:
        """Abort an in-flight command capture without firing a keystroke."""
        if not self._command_capturing:
            return
        logger.info("Cancelling command capture")
        self._command_capturing = False
        self._silence_poll_timer.stop()
        self._recorder.cancel()
        self._saved_hwnd = None
        self.state_changed.emit(STATE_IDLE, "Command cancelled")
        QTimer.singleShot(1500, lambda: self.state_changed.emit(STATE_IDLE, "Ready"))

    def _on_streaming_tentative(self, text: str) -> None:
        """Tentative tail update — currently just logged.

        Future: render as a faint overlay on/near the bar strip so the user
        sees what's still flickering. Not visualised yet to keep S3 small.
        """
        if text:
            logger.debug("Streaming tentative: %r", text[:80])

    def _on_error(self, message: str) -> None:
        """Handle error (UI thread)."""
        logger.error("Error occurred: %s", message)
        self._timeout_timer.stop()
        self._processing = False
        self._callout.clear()
        self._saved_hwnd = None
        self.state_changed.emit(STATE_ERROR, message)

        # Cancel any existing error recovery timer
        if self._error_recovery_timer_id is not None:
            self.killTimer(self._error_recovery_timer_id)
            self._error_recovery_timer_id = None

        # Start cancellable error recovery timer (3 seconds)
        self._error_recovery_timer_id = self.startTimer(3000)
        logger.debug("Error recovery timer started (id=%s)", self._error_recovery_timer_id)

    def timerEvent(self, event: QTimerEvent) -> None:
        """Handle timer events (error recovery)."""
        timer_id = event.timerId()

        if timer_id == self._error_recovery_timer_id:
            # Kill the timer so it doesn't fire again
            self.killTimer(timer_id)
            self._error_recovery_timer_id = None

            # Only recover if still in error state — if user pressed hotkey
            # during the 3s window, state will have changed and we skip
            if self._state == STATE_ERROR:
                logger.info("Error recovery timer fired, returning to idle")
                self.state_changed.emit(STATE_IDLE, "Ready")
            else:
                logger.debug("Error recovery timer fired but state is %s, skipping", self._state)
        else:
            super().timerEvent(event)

    def _track_foreground_window(self) -> None:
        """Poll the foreground window, keeping the last non-self HWND.

        Runs every 250ms via QTimer. Only records windows belonging to
        other processes so that widget/tray clicks have a correct target.
        """
        hwnd = get_foreground_window_if_external()
        if hwnd:
            self._last_external_hwnd = hwnd

    def _on_hotkey_pressed(self) -> None:
        """Handle hotkey press (from hotkey thread).

        Captures an EXTERNAL foreground window — never our own. If the user
        clicked our widget/callout before pressing the hotkey, the raw
        foreground HWND would be ours, and we'd later 'restore' focus to
        ourselves and paste into nothing. Fix: filter by process ID, and
        fall back to the polled tracker's last external HWND.
        """
        hwnd = get_foreground_window_if_external()
        if not hwnd:
            hwnd = self._last_external_hwnd
            logger.info("Hotkey: foreground was self, using tracked HWND=%s", hwnd)
        else:
            logger.info("Hotkey pressed, saved HWND=%s", hwnd)
        self._hotkey_signal.emit(hwnd)

    def _on_command_hotkey_pressed(self) -> None:
        """Command-only capture hotkey pressed (hotkey thread).

        Same external-HWND filter as the dictation hotkey. Emits to UI
        thread via _command_hotkey_signal.
        """
        hwnd = get_foreground_window_if_external()
        if not hwnd:
            hwnd = self._last_external_hwnd
            logger.info("Command hotkey: foreground was self, tracked HWND=%s", hwnd)
        else:
            logger.info("Command hotkey pressed, HWND=%s", hwnd)
        self._command_hotkey_signal.emit(hwnd)

    def _on_widget_clicked(self) -> None:
        """Handle widget click — use tracked external HWND then toggle.

        Clicking the widget makes it foreground BEFORE this handler runs,
        so save_foreground_window() would capture our own widget. Instead
        we use the last external HWND from the focus tracker.
        """
        hwnd = self._last_external_hwnd
        title = get_window_title(hwnd) if hwnd else "(none)"
        logger.info("Widget clicked, using tracked HWND=%s title='%s'", hwnd, title)
        self._toggle_with_focus(hwnd)

    def _on_tray_toggle(self) -> None:
        """Handle tray toggle — use tracked external HWND then toggle.

        Same as widget click: the tray menu steals focus before this runs.
        """
        hwnd = self._last_external_hwnd
        title = get_window_title(hwnd) if hwnd else "(none)"
        logger.info("Tray toggle, using tracked HWND=%s title='%s'", hwnd, title)
        self._toggle_with_focus(hwnd)

    def _toggle_with_focus(self, saved_hwnd: int | None) -> None:
        """Toggle recording with a saved foreground window handle."""
        # Only save HWND when starting a new recording (not when stopping)
        if self._state == STATE_IDLE:
            self._saved_hwnd = saved_hwnd
        self.toggle_recording()

    # ── Command-only capture lifecycle ────────────────────────────────────

    def _toggle_command_capture(self, saved_hwnd: int | None) -> None:
        """Single-press command lifecycle (UI thread).

        Press → start. The session ends automatically: VAD detects silence
        after speech and fires the command, OR cancels after the no-speech
        timeout. A SECOND hotkey press during capture means CANCEL — the
        user is aborting (e.g. they said the wrong thing). Mutually
        exclusive with dictation: ignored if dictation is in flight.
        """
        if self._command_capturing:
            # Second press = cancel, not fire. The fire path is VAD-driven.
            self._cancel_command_capture()
            return

        # Refuse if dictation/processing is active — clear UX over magic.
        if self._state != STATE_IDLE:
            logger.info("Command hotkey ignored: state=%s (not IDLE)", self._state)
            return

        self._saved_hwnd = saved_hwnd
        self._start_command_capture()

    def _start_command_capture(self) -> None:
        """Begin recording for a command. Single-press UX: VAD auto-stop
        fires after the user finishes speaking (or auto-cancel if they
        never speak), so they don't need to press the hotkey again.
        """
        if self._recorder.is_recording():
            logger.debug("Command capture refused: recorder already busy")
            return
        logger.info("Starting command capture")
        # Distinct visual identity (orange) from dictation (blue).
        self.state_changed.emit(STATE_COMMAND, "Command...")
        try:
            self._recorder.start()
        except Exception as e:
            logger.exception("Recorder failed to start (command): %s", e)
            self._saved_hwnd = None
            self.error_occurred.emit(
                "Microphone unavailable. Check Settings → Audio device."
            )
            return
        self._command_capturing = True
        # Reset and start the silence monitor so the poll timer can decide
        # when speech-ended → fire, or no-speech-ever → cancel.
        self._silence_monitor.reset()
        self._silence_poll_timer.start(SILENCE_POLL_INTERVAL_MS)

    def _stop_command_capture(self) -> None:
        """Stop command recording, transcribe, classify (no wake word), fire."""
        if not self._command_capturing:
            return
        logger.info("Stopping command capture")
        self._command_capturing = False
        self._silence_poll_timer.stop()
        self.state_changed.emit(STATE_PROCESSING, "Recognizing command...")
        self._processing = True

        audio_path = self._recorder.stop()
        if audio_path is None or not validate_audio(audio_path):
            logger.warning("Command capture: no audio")
            self._processing = False
            self._saved_hwnd = None
            self.error_occurred.emit("No audio for command")
            return

        # Transcribe in background; result handled by _on_command_transcribed
        threading.Thread(
            target=self._transcribe_command,
            args=(audio_path,),
            daemon=True,
        ).start()

    def _transcribe_command(self, audio_path: Path) -> None:
        """Background-thread transcription for command capture."""
        try:
            recognizer = self._local_recognizer
            recognizer.set_model(self._settings.model)
            # No initial_prompt for commands — vocabulary bias would push
            # the model AWAY from short command words.
            result = recognizer.transcribe(audio_path, self._settings.language)
            try:
                os.unlink(audio_path)
            except Exception:
                pass

            if not result.success or not result.text.strip():
                self.error_occurred.emit(result.error or "No speech detected")
                return

            classification, cmd_result = classify_transcription(
                result.text,
                threshold=self._settings.command_threshold,
                require_wake_word=False,
            )
            self._processing = False
            if classification == "command" and cmd_result:
                self.command_detected.emit(cmd_result)
            else:
                logger.info("Command capture: no match for %r", result.text[:60])
                # Surface as error so the user sees something happened
                self.error_occurred.emit(f"No command match: {result.text.strip()}")
        except Exception as e:
            logger.exception("Command transcription error: %s", e)
            self._processing = False
            self.error_occurred.emit(str(e))

    def toggle_recording(self) -> None:
        """Toggle recording state."""
        if self._processing:
            logger.debug("Toggle recording ignored: currently processing")
            return  # Don't interrupt processing

        if self._state == STATE_ERROR:
            # User pressed hotkey during error display — cancel error timer and go to idle
            logger.info("Toggle recording during error state: cancelling error recovery")
            if self._error_recovery_timer_id is not None:
                self.killTimer(self._error_recovery_timer_id)
                self._error_recovery_timer_id = None
            self.state_changed.emit(STATE_IDLE, "Ready")
            return

        if self._state == STATE_RECORDING:
            logger.debug("Toggle recording: stopping")
            self._stop_recording()
        elif self._state == STATE_IDLE:
            logger.debug("Toggle recording: starting")
            self._start_recording()
        else:
            logger.debug("Toggle recording ignored: state is %s", self._state)

    def _start_recording(self) -> None:
        """Start recording audio (streaming or batch mode).

        Recorder is started FIRST so a hardware/device failure doesn't leave
        the streaming wiring half-up (which would then immediately auto-stop
        and mask the real error). Streaming attaches only after the audio
        stream is open.
        """
        if self._recorder.is_recording():
            logger.debug("Start recording ignored: already recording")
            return

        logger.info("Starting audio recording (streaming=%s)", self._settings.streaming_mode)
        self.state_changed.emit(STATE_RECORDING, "Recording...")

        try:
            self._recorder.start()
        except Exception as e:
            logger.exception("Recorder failed to start: %s", e)
            self.error_occurred.emit(
                "Microphone unavailable. Check Settings → Audio device, "
                "then Tray → Reset State."
            )
            return

        if self._settings.streaming_mode:
            self._start_streaming()

    def _start_streaming(self) -> None:
        """Spin up the streaming transcriber and hook the recorder to feed it."""
        vocab = self._settings.custom_vocabulary
        initial_prompt = ", ".join(vocab) if vocab else None

        # Ensure the streaming recognizer matches the user's chosen model.
        # set_model is cheap when unchanged; reloads on first use otherwise.
        self._streaming_recognizer.set_model(self._settings.streaming_model)

        self._streaming_injected_any = False
        self._streamer = StreamingTranscriber(
            self._streaming_recognizer,
            sample_rate=SAMPLE_RATE,
            window_seconds=STREAM_WINDOW_SECONDS,
            interval_seconds=STREAM_INTERVAL_SECONDS,
            language=self._settings.language,
            initial_prompt=initial_prompt,
            vad_min_silence_ms=STREAM_VAD_MIN_SILENCE_MS,
            on_committed=lambda t: self.streaming_committed.emit(t),
            on_tentative=lambda t: self.streaming_tentative.emit(t),
        )
        self._streamer.start()
        # Recorder feeds raw chunks straight into the streamer's buffer.
        self._recorder.set_chunk_callback(self._streamer.feed)
        # VAD lifecycle: reset silence monitor + start the poll timer so
        # auto-pause/auto-stop transitions can fire on the UI thread.
        self._silence_monitor.reset()
        self._silence_poll_timer.start(SILENCE_POLL_INTERVAL_MS)
        logger.info("Streaming mode active")

    def _stop_recording(self) -> None:
        """Stop recording. In streaming mode, finalize stream; in batch, transcribe."""
        if not self._recorder.is_recording():
            logger.debug("Stop recording ignored: not recording")
            return

        if self._streamer is not None:
            self._stop_streaming()
            return

        # Batch mode: existing record-then-transcribe path
        logger.info("Stopping audio recording")
        self.state_changed.emit(STATE_PROCESSING, "Processing...")
        self._processing = True

        # Stop recording and get audio file
        audio_path = self._recorder.stop()
        logger.debug("Audio saved to: %s", audio_path)

        if audio_path is None or not validate_audio(audio_path):
            logger.warning("No valid audio recorded")
            self.error_occurred.emit("No audio recorded")
            return

        logger.info("Starting transcription in background thread")
        # Process in background thread
        self._transcription_thread = threading.Thread(
            target=self._process_audio,
            args=(audio_path,),
            daemon=True
        )
        self._transcription_thread.start()

        # Start transcription timeout (cancellable — prevents stale timeouts
        # from earlier transcriptions from firing during a new one)
        self._timeout_timer.start(TRANSCRIPTION_TIMEOUT_SECONDS * 1000)

    def _stop_streaming(self) -> None:
        """Tear down streaming. Recorder keeps the WAV around as a fallback
        but we don't transcribe it again — the streamer already produced
        committed text mid-flight.
        """
        logger.info("Stopping streaming")
        # Stop polling FIRST so a tick mid-teardown can't re-trigger transitions.
        self._silence_poll_timer.stop()
        # Detach the chunk callback so no further audio reaches the streamer
        # after we ask it to stop.
        self._recorder.set_chunk_callback(None)
        # Cancel rather than stop() so we don't write a redundant WAV.
        self._recorder.cancel()
        if self._streamer:
            self._streamer.stop()
            self._streamer = None
        # No PROCESSING phase in streaming — text was injected as it came.
        self.state_changed.emit(STATE_IDLE, "Done!")
        QTimer.singleShot(1500, lambda: self.state_changed.emit(STATE_IDLE, "Ready"))

    def _check_transcription_timeout(self) -> None:
        """Check if transcription has timed out."""
        if self._processing and self._transcription_thread and self._transcription_thread.is_alive():
            logger.error("Transcription timed out after %d seconds", TRANSCRIPTION_TIMEOUT_SECONDS)
            self._processing = False
            self._transcription_thread = None
            self.error_occurred.emit(
                f"Transcription timed out after {TRANSCRIPTION_TIMEOUT_SECONDS}s. "
                "Try a shorter recording or use Reset State."
            )

    def _process_audio(self, audio_path: Path) -> None:
        """Process audio file (runs in background thread)."""
        try:
            # Select recognizer
            if self._settings.engine == ENGINE_API:
                logger.debug("Using API recognizer")
                recognizer = self._api_recognizer
                recognizer.set_api_key(self._settings.openai_api_key)
            else:
                logger.debug("Using local recognizer with model: %s", self._settings.model)
                recognizer = self._local_recognizer
                recognizer.set_model(self._settings.model)

            # Build initial_prompt from custom vocabulary.
            # Presence of words = active. Empty list = no prompt sent.
            initial_prompt = None
            vocab = self._settings.custom_vocabulary
            if vocab:
                initial_prompt = ", ".join(vocab)
                logger.debug("Custom vocabulary active: %d words", len(vocab))

            # Transcribe with segment streaming
            logger.debug("Transcribing audio with language: %s", self._settings.language)
            result = recognizer.transcribe(
                audio_path, self._settings.language,
                segment_callback=self._emit_segment,
                initial_prompt=initial_prompt,
            )
            logger.debug("Transcription result: %s", result)

            # Clean up temp file
            try:
                os.unlink(audio_path)
                logger.debug("Cleaned up temp audio file: %s", audio_path)
            except Exception as e:
                logger.warning("Failed to clean up temp audio file: %s", e)

            if result.success:
                # Classify raw text as command vs dictation BEFORE cleanup
                # (cleanup adds punctuation/capitalization that can hurt fuzzy match).
                # Skip classification entirely when commands are disabled.
                if self._settings.commands_enabled:
                    classification, cmd_result = classify_transcription(
                        result.text,
                        threshold=self._settings.command_threshold,
                    )
                else:
                    classification, cmd_result = ("dictation", None)
                if classification == "command" and cmd_result:
                    logger.info("Classified as command: %s", cmd_result)
                    self.command_detected.emit(cmd_result)
                else:
                    # Clean up text and emit as dictation
                    text = cleanup_text(result.text)
                    logger.info("Transcription successful")
                    self.transcription_complete.emit(text)
            else:
                logger.warning("Transcription failed: %s", result.error)
                self.error_occurred.emit(result.error or "Transcription failed")

        except Exception as e:
            logger.exception("Exception during audio processing: %s", e)
            self.error_occurred.emit(str(e))
        finally:
            # Ensure _processing is always cleared, even if signal emission
            # fails during shutdown
            self._processing = False
            self._transcription_thread = None

    def _emit_segment(self, text: str) -> None:
        """Emit a transcription segment signal (called from background thread)."""
        logger.info("Segment received: %s", text[:60] + "..." if len(text) > 60 else text)
        self.transcription_segment.emit(text)

    def _on_segment(self, text: str) -> None:
        """Handle a transcription segment (UI thread)."""
        logger.info("Displaying segment in callout")
        self._callout.append_segment(text)

    def _show_widget(self) -> None:
        """Show the floating widget."""
        logger.debug("Showing floating widget")
        if self._widget:
            self._widget.show()
            self._settings.show_widget = True
        if self._tray:
            self._tray.set_widget_visible(True)

    def _hide_widget(self) -> None:
        """Hide the floating widget."""
        logger.debug("Hiding floating widget")
        if self._widget:
            # Save position before hiding
            self._settings.widget_position = self._widget.save_position()
            self._widget.hide()
            self._settings.show_widget = False
        if self._tray:
            self._tray.set_widget_visible(False)

    def _open_settings(self) -> None:
        """Open settings window."""
        logger.debug("Opening settings window")
        if self._settings_window is None:
            logger.debug("Creating new settings window instance")
            self._settings_window = SettingsWindow()
            self._settings_window.settings_changed.connect(self._on_settings_changed)
            self._settings_window.hotkey_changed.connect(self._on_hotkey_changed)
            self._settings_window.command_hotkey_changed.connect(self._on_command_hotkey_changed)
            self._settings_window.widget_size_changed.connect(self._on_widget_size_changed)

        # Ensure window is visible and focused
        self._settings_window.showNormal()
        self._settings_window.raise_()
        self._settings_window.activateWindow()

    def _on_settings_changed(self) -> None:
        """Handle settings change."""
        logger.info("Settings changed, updating components")
        # Update recorder device
        logger.debug("Updating audio device to: %s", self._settings.audio_device)
        self._recorder.set_device(self._settings.audio_device)

        # Update recognizer model
        logger.debug("Updating model to: %s", self._settings.model)
        self._local_recognizer.set_model(self._settings.model)

        # Update API key
        logger.debug("Updating API key")
        self._api_recognizer.set_api_key(self._settings.openai_api_key)

    def _on_hotkey_changed(self, hotkey: dict) -> None:
        """Handle dictation hotkey change."""
        logger.info("Dictation hotkey changed to: %s", hotkey)
        self._hotkey_manager.stop()
        self._hotkey_manager.set_hotkey(hotkey)
        self._hotkey_manager.start()
        logger.debug("Dictation hotkey listener restarted")

    def _on_command_hotkey_changed(self, hotkey: dict) -> None:
        """Handle command hotkey change."""
        logger.info("Command hotkey changed to: %s", hotkey)
        self._command_hotkey_manager.stop()
        self._command_hotkey_manager.set_hotkey(hotkey)
        self._command_hotkey_manager.start()
        logger.debug("Command hotkey listener restarted")

    def _on_widget_size_changed(self, size_key: str) -> None:
        """Handle widget size change."""
        logger.info("Widget size changed to: %s", size_key)
        if self._widget:
            self._widget.set_size(size_key)

    def _reset_state(self) -> None:
        """Reset the app to idle state. Used to recover from stuck states."""
        logger.info("Resetting application state")

        # Cancel error recovery timer
        if self._error_recovery_timer_id is not None:
            self.killTimer(self._error_recovery_timer_id)
            self._error_recovery_timer_id = None

        # Clear processing flag
        self._processing = False
        self._transcription_thread = None
        self._saved_hwnd = None
        self._command_capturing = False
        self._streaming_injected_any = False

        # Stop the VAD poll timer if it was running for either modality
        self._silence_poll_timer.stop()

        # Tear down any active streamer (worker thread + buffer) so reset
        # doesn't leave an orphan thread feeding callbacks into a UI that
        # thinks it's idle.
        if self._streamer is not None:
            try:
                self._recorder.set_chunk_callback(None)
                self._streamer.stop()
            except Exception as e:
                logger.warning("Error stopping streamer during reset: %s", e)
            self._streamer = None

        # Hide callout
        self._callout.clear()

        # Force-close any audio stream
        self._recorder.close_stream()

        # Return to idle
        self.state_changed.emit(STATE_IDLE, "Ready")

        # Notify user
        if self._tray:
            self._tray.show_message(
                "Whisper Voice Input",
                "State has been reset. Ready for recording.",
                3000
            )
        logger.info("Application state reset complete")

    def _restart_app(self) -> None:
        """Restart the entire application process."""
        logger.info("Application restart initiated")

        # Save widget position
        if self._widget and self._widget.isVisible():
            self._settings.widget_position = self._widget.save_position()

        # Stop everything
        self._focus_tracker.stop()
        self._silence_poll_timer.stop()
        self._hotkey_manager.stop()
        self._command_hotkey_manager.stop()
        if self._streamer is not None:
            try:
                self._streamer.stop()
            except Exception:
                pass
            self._streamer = None
        self._recorder.close_stream()

        # Hide UI
        self._callout.clear()
        if self._widget:
            self._widget.hide()
        if self._tray:
            self._tray.hide()

        # Replace the current process with a fresh one
        logger.info("Restarting process: %s %s", sys.executable, sys.argv)
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            logger.error("Failed to restart: %s", e)
            # Fallback: just quit and let user restart manually
            if self._tray:
                self._tray.show()
                self._tray.show_message(
                    "Whisper Voice Input",
                    f"Restart failed: {e}. Please restart manually.",
                    5000
                )

    def quit(self) -> None:
        """Quit the application."""
        logger.info("Application shutdown initiated")

        # Save widget position
        if self._widget and self._widget.isVisible():
            logger.debug("Saving widget position")
            self._settings.widget_position = self._widget.save_position()

        # Stop focus tracker, silence poll, and hotkey listeners
        self._focus_tracker.stop()
        self._silence_poll_timer.stop()
        logger.debug("Stopping hotkey listeners")
        self._hotkey_manager.stop()
        self._command_hotkey_manager.stop()

        # Stop any active streamer
        if self._streamer is not None:
            try:
                self._streamer.stop()
            except Exception:
                pass
            self._streamer = None

        # Cancel any recording
        logger.debug("Cancelling any active recording")
        self._recorder.cancel()

        # Hide UI
        logger.debug("Hiding UI components")
        self._callout.clear()
        if self._widget:
            self._widget.hide()
        if self._tray:
            self._tray.hide()

        # Quit app
        logger.info("Application shutdown complete")
        self._app.quit()

    def run(self) -> int:
        """Run the application."""
        logger.info("Starting Qt event loop")
        return self._app.exec()
