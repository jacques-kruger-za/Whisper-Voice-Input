# Whisper Voice Input - Claude Code Instructions

## Project Overview

A Windows desktop voice-to-text application using OpenAI's Whisper model for speech recognition. Provides a floating widget UI with audio-reactive visualizations and system tray integration.

## Tech Stack

- **Language**: Python 3.10+
- **UI Framework**: PyQt6
- **Speech Recognition**: Faster-Whisper (local) / OpenAI API (cloud)
- **Audio**: sounddevice + numpy/scipy
- **Hotkeys**: pynput (global keyboard listener)
- **Text Injection**: pyperclip + pyautogui (clipboard paste)

## Project Structure

```
src/
├── main.py              # Entry point
├── app.py               # Main application controller
├── config/              # Settings & constants
│   ├── constants.py     # App-wide constants, colors, sizes
│   └── settings.py      # JSON settings persistence
├── audio/               # Audio capture
│   ├── recorder.py      # Microphone recording (sounddevice)
│   └── processor.py     # Audio validation
├── recognition/         # Speech-to-text engines
│   ├── base.py          # Abstract recognizer interface
│   ├── whisper_local.py # Faster-Whisper (offline)
│   ├── whisper_api.py   # OpenAI Whisper API
│   └── cleanup.py       # Text post-processing
├── input/               # User input handling
│   ├── hotkey.py        # Global hotkey manager
│   └── injector.py      # Clipboard text injection
└── ui/                  # PyQt6 interface
    ├── widget.py        # Floating circular widget with animations
    ├── tray.py          # System tray icon
    ├── settings.py      # Settings dialog
    └── styles.py        # Qt stylesheets & color palette
```

## Key Files to Modify

| Task | Files |
|------|-------|
| Add new language | `src/config/constants.py` (SUPPORTED_LANGUAGES) |
| Change hotkey default | `src/config/constants.py` (DEFAULT_HOTKEY) |
| Modify widget animations | `src/ui/widget.py` (FrequencyBar, PulseRing classes) |
| Change colors/theme | `src/ui/styles.py` |
| Add new recognition engine | `src/recognition/` (extend BaseRecognizer) |
| Modify text cleanup | `src/recognition/cleanup.py` |

## State Machine

The app uses four states defined in `constants.py`:
- `STATE_IDLE` - Ready, waiting for input
- `STATE_RECORDING` - Capturing audio from microphone
- `STATE_PROCESSING` - Transcribing audio
- `STATE_ERROR` - Error occurred (auto-clears after 3s)

## Threading Model

- **Main Thread**: Qt event loop, UI updates
- **Hotkey Thread**: pynput listener (background daemon)
- **Recording Thread**: sounddevice callback (real-time audio)
- **Recognition Thread**: Whisper transcription (spawned per request)

Use Qt signals (`pyqtSignal`) for cross-thread UI updates.

## Settings Storage

Location: `%AppData%/Whisper Voice Input/settings.json`

Managed by `Settings` class in `src/config/settings.py` with auto-save on property changes.

## Running the App

```bash
# Development
python -m src.main

# Without console window
pythonw -m src.main

# Build standalone exe
pip install pyinstaller
pyinstaller --name "Whisper Voice Input" --windowed --onefile src/main.py
```

## Common Tasks

### Adding a new Whisper model option
1. Add to `WHISPER_MODELS` list in `src/config/constants.py`

### Changing widget sizes
1. Modify `WIDGET_SIZES` dict in `src/config/constants.py`
2. Adjust `THICKNESS_SCALE` in `src/ui/widget.py` if needed

### Adding filler words to remove
1. Add to `FILLER_WORDS` list in `src/config/constants.py`

## Dependencies

All deps in `requirements.txt`. Key ones:
- `faster-whisper` - Local speech recognition (downloads models from HuggingFace)
- `openai` - Cloud API client
- `PyQt6` - UI framework
- `pynput` - Global hotkey capture
- `sounddevice` - Audio recording

## Notes

- First run downloads Whisper model (~150MB for "base")
- API engine requires OpenAI API key (costs money per request)
- Local engine runs entirely offline after initial model download
- Widget uses 60fps animation timer for smooth visualizations
- Text injection uses clipboard (may interfere with user's clipboard briefly)
