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
- **Logging**: Python `logging` module with file + console output

## Project Structure

```
src/
├── main.py              # Entry point with startup logging and error handling
├── app.py               # Main application controller with comprehensive logging
├── config/              # Settings, constants & logging
│   ├── constants.py     # App-wide constants, colors, sizes
│   ├── settings.py      # JSON settings persistence
│   └── logging_config.py # Centralized logging configuration
├── audio/               # Audio capture
│   ├── recorder.py      # Microphone recording (sounddevice)
│   └── processor.py     # Audio validation with error logging
├── recognition/         # Speech-to-text engines
│   ├── base.py          # Abstract recognizer interface
│   ├── whisper_local.py # Faster-Whisper (offline) with progress logging
│   ├── whisper_api.py   # OpenAI Whisper API with error logging
│   └── cleanup.py       # Text post-processing
├── input/               # User input handling
│   ├── hotkey.py        # Global hotkey manager with debug logging
│   └── injector.py      # Clipboard text injection with error logging
└── ui/                  # PyQt6 interface
    ├── widget.py        # Floating circular widget with animations
    ├── tray.py          # System tray icon with debug logging
    ├── settings.py      # Settings dialog with error logging
    └── styles.py        # Qt stylesheets & color palette
```

## Key Files to Modify

| Task | Files |
|------|-------|
| Add new language | `src/config/constants.py` (SUPPORTED_LANGUAGES) |
| Change hotkey default | `src/config/constants.py` (DEFAULT_HOTKEY) |
| Modify widget animations | `src/ui/widget.py` (PulseRing class) |
| Change colors/theme | `src/ui/styles.py` |
| Add new recognition engine | `src/recognition/` (extend BaseRecognizer) |
| Modify text cleanup | `src/recognition/cleanup.py` |
| Configure logging | `src/config/logging_config.py` (log level, format, handlers) |
| Change log location | `src/config/logging_config.py` (uses platformdirs) |

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

## Logging Configuration

### Log Location

- **Windows**: `%LOCALAPPDATA%/Whisper Voice Input/Logs/app.log`
- Managed by `LoggingConfig` class in `src/config/logging_config.py`
- Uses `platformdirs` for cross-platform log directory resolution

### Log Format

```
2024-01-15 10:30:45 - Whisper Voice Input.app - INFO - Application initialized
```

Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

### Using the Logger

Get a module-specific logger anywhere in the codebase:

```python
from src.config import get_logger

logger = get_logger(__name__)

# Usage
logger.debug("Detailed debugging info")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.exception("Error with stack trace")  # Use in except blocks
```

### Log Levels by Component

| Component | Level | What's Logged |
|-----------|-------|---------------|
| `main` | INFO | Startup info, version, platform |
| `app` | INFO/DEBUG | State changes, lifecycle events, errors |
| `recorder` | DEBUG/WARNING | Device selection, recording state, stream issues |
| `processor` | WARNING | Audio validation errors |
| `whisper_local` | INFO/ERROR | Model loading, transcription completion, errors |
| `whisper_api` | DEBUG/INFO/ERROR | API calls, transcription results, errors |
| `hotkey` | DEBUG | Key events, listener lifecycle |
| `injector` | ERROR | Text injection failures |
| `tray` | DEBUG | Icon state changes, menu events |
| `settings` | ERROR | Autostart failures |

### Configuring Log Level

At application startup in `src/main.py`:

```python
from src.config import configure_logging
import logging

# Default (INFO level)
configure_logging()

# Debug level for development
configure_logging(logging.DEBUG)
```

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

### Enabling debug logging
1. In `src/main.py`, change `configure_logging()` to `configure_logging(logging.DEBUG)`
2. Or set environment variable before running (not currently implemented)

### Viewing logs
1. Check `%LOCALAPPDATA%/Whisper Voice Input/Logs/app.log`
2. Console output also shows logs when running via `python -m src.main`

## Dependencies

All deps in `requirements.txt`. Key ones:
- `faster-whisper` - Local speech recognition (downloads models from HuggingFace)
- `openai` - Cloud API client
- `PyQt6` - UI framework
- `pynput` - Global hotkey capture
- `sounddevice` - Audio recording
- `platformdirs` - Cross-platform directory resolution (settings, logs)

## Notes

- First run downloads Whisper model (~150MB for "base")
- API engine requires OpenAI API key (costs money per request)
- Local engine runs entirely offline after initial model download
- Widget uses 60fps animation timer for smooth visualizations
- Text injection uses clipboard (may interfere with user's clipboard briefly)
- Logs are written to both console and file for debugging
- All modules use structured logging via `get_logger()` from config package
