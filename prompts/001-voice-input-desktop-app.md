<objective>
Build a Windows desktop voice input application that serves as a universal keyboard alternative. Users activate voice recording via global hotkey or system tray, speak naturally, and the transcribed text is automatically inserted into any focused text field across any application.

This tool replaces typing for users who prefer voice input - it must be fast, reliable, and work seamlessly with any application that accepts keyboard input.
</objective>

<context>
This is a productivity tool for voice-first input. The user activates recording, speaks, and the transcribed text appears where they're typing - whether that's a browser, text editor, chat app, or any other application.

Key user expectations:
- Minimal setup: Install and use immediately
- High accuracy: AI-powered transcription that handles natural speech
- Universal compatibility: Works with any text input field system-wide
- Efficient: Low resource usage, fast transcription
- Visual feedback: Clear indication of recording state
</context>

<tech_stack>
- **Language**: Python 3.10+
- **UI Framework**: PyQt6 (modern, well-maintained, good Windows support)
- **Speech Recognition**: Faster-Whisper (local, fast, high accuracy)
- **Fallback**: OpenAI Whisper API (user-configured in settings)
- **Audio Capture**: sounddevice or pyaudio
- **Text Injection**: pyperclip + pyautogui (clipboard paste simulation)
- **Global Hotkey**: pynput or keyboard library
- **System Tray**: PyQt6 QSystemTrayIcon
</tech_stack>

<requirements>

<core_features>
1. **Global Hotkey Toggle Recording**
   - Customizable hotkey (default: Ctrl+Shift+Space)
   - Press once to start recording, press again to stop and process
   - Works even when app is not focused

2. **Floating Widget**
   - Small, always-on-top draggable window
   - Clear visual states: Idle, Recording (with audio waveform/level visualization), Processing
   - Minimal footprint when idle
   - Can be hidden/shown from tray

3. **System Tray Integration**
   - Tray icon with context menu
   - Quick access to: Start/Stop recording, Settings, Show/Hide widget, Exit
   - Icon changes based on state (idle/recording/processing)

4. **Voice Recognition**
   - Primary: Faster-Whisper with bundled model (medium.en or large-v3)
   - Fallback: OpenAI Whisper API (user provides API key in settings)
   - Manual switch between local/API in settings

5. **Text Processing Pipeline**
   - Capture audio → Transcribe → Basic cleanup → Inject into focused field
   - Basic cleanup: Fix capitalization, punctuation, remove filler words (um, uh, like)
   - Use clipboard + Ctrl+V simulation for injection (faster than keystroke simulation)

6. **Language Support (out of box)**
   - English US
   - English UK
   - English South Africa
   - Other languages: optional/configurable in settings
</core_features>

<settings_window>
From tray icon, open full settings window with:
- Hotkey configuration (capture new hotkey)
- Audio input device selection
- Recognition engine toggle (Local Faster-Whisper / OpenAI API)
- OpenAI API key input (for API mode)
- Model selection (for local: tiny, base, small, medium, large)
- Language selection
- Startup with Windows toggle
- Widget position/visibility preferences
</settings_window>

<efficiency_requirements>
- Idle CPU usage: <1%
- Memory usage: <200MB (excluding model, model loads on-demand)
- Transcription latency: <3 seconds for 30 seconds of audio (with medium model)
- Model loading: Lazy load on first use, keep warm for subsequent uses
</efficiency_requirements>

</requirements>

<architecture>

```
whisper-voice-input/
├── src/
│   ├── main.py              # Entry point, app initialization
│   ├── app.py               # Main application class
│   ├── ui/
│   │   ├── widget.py        # Floating recording widget
│   │   ├── settings.py      # Settings window
│   │   ├── tray.py          # System tray integration
│   │   └── styles.py        # Qt stylesheets
│   ├── audio/
│   │   ├── recorder.py      # Audio capture
│   │   └── processor.py     # Audio preprocessing
│   ├── recognition/
│   │   ├── base.py          # Abstract recognizer interface
│   │   ├── whisper_local.py # Faster-Whisper implementation
│   │   ├── whisper_api.py   # OpenAI API implementation
│   │   └── cleanup.py       # Text post-processing
│   ├── input/
│   │   ├── hotkey.py        # Global hotkey handling
│   │   └── injector.py      # Text injection (clipboard + paste)
│   └── config/
│       ├── settings.py      # Settings management
│       └── constants.py     # App constants
├── resources/
│   ├── icons/               # Tray and widget icons
│   └── models/              # Downloaded Whisper models (gitignored)
├── requirements.txt
├── setup.py                 # For creating installer
└── README.md
```

</architecture>

<implementation_guidance>

<step_1>
Set up project structure and dependencies:
- Create virtual environment
- Install: PyQt6, faster-whisper, sounddevice, pyperclip, pyautogui, pynput
- Create basic app skeleton with main.py entry point
</step_1>

<step_2>
Implement audio recording:
- Use sounddevice for microphone capture
- Record to temporary WAV file
- Handle device selection from settings
</step_2>

<step_3>
Implement Faster-Whisper recognition:
- Lazy-load model on first transcription
- Support model selection (tiny→large)
- Implement language detection or use specified language
- Handle errors gracefully (model not found, GPU not available)
</step_3>

<step_4>
Implement text cleanup:
- Basic punctuation/capitalization fixes
- Remove filler words
- Keep it simple and fast
</step_4>

<step_5>
Implement text injection:
- Copy processed text to clipboard
- Simulate Ctrl+V keypress
- Small delay to ensure paste completes
</step_5>

<step_6>
Build floating widget:
- PyQt6 frameless window, always-on-top
- Draggable by clicking anywhere
- Visual states with smooth transitions
- Audio level visualization during recording
</step_6>

<step_7>
Implement system tray:
- QSystemTrayIcon with context menu
- State-aware icon changes
- Left-click: toggle widget, Right-click: menu
</step_7>

<step_8>
Global hotkey handling:
- Use pynput for system-wide hotkey capture
- Configurable hotkey stored in settings
- Handle hotkey conflicts gracefully
</step_8>

<step_9>
Settings window:
- Full configuration UI
- Save/load from JSON config file
- Apply changes immediately where possible
</step_9>

<step_10>
OpenAI API fallback:
- Implement alternative recognizer using openai library
- User provides API key in settings
- Manual switch (not auto-fallback)
</step_10>

</implementation_guidance>

</requirements>

<constraints>
- **Windows-first**: Optimize for Windows, don't worry about cross-platform initially
- **Minimal dependencies**: Avoid unnecessary libraries, keep installer small
- **No external services required**: Local model must work offline after initial setup
- **Clipboard awareness**: Warn user that voice input will use clipboard (brief flash)
- **Error resilience**: If recognition fails, show error in widget, don't crash
</constraints>

<output>
Create all files in the project structure above using relative paths:
- `./src/main.py` - Entry point
- `./src/app.py` - Main application
- All other files as specified in architecture

Include a `./requirements.txt` with pinned versions.
Include a `./README.md` with setup and usage instructions.
</output>

<verification>
Before declaring complete, verify:
1. App launches without errors: `python src/main.py`
2. Floating widget appears and is draggable
3. System tray icon shows with working menu
4. Global hotkey toggles recording state
5. Recording captures audio (check temp file created)
6. Transcription produces text output (test with spoken phrase)
7. Text injection works (test in Notepad)
8. Settings window opens and saves configuration

Run each verification step and fix any issues found.
</verification>

<success_criteria>
- User can install app with `pip install -r requirements.txt`
- First-run automatically downloads Whisper model if needed
- User speaks "Hello world" and sees it typed into Notepad
- Widget clearly shows recording/processing/idle states
- Settings persist across app restarts
- App runs efficiently in background without noticeable CPU usage
</success_criteria>
