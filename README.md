# Whisper Voice Input

A Windows desktop application that converts speech to text using OpenAI's Whisper model. Works as a universal keyboard alternative - dictate text into any application.

## Features

- **Global Hotkey** (Ctrl+Shift+Space) - Works from any application
- **Floating Widget** - Circular status indicator with audio-reactive animations
- **System Tray** - Minimize to tray, quick access menu
- **Dual Engines** - Local (offline) or OpenAI API (cloud)
- **Real-time Feedback** - Visual audio level display during recording
- **Text Cleanup** - Removes filler words, fixes punctuation
- **Customizable** - Widget size, hotkey, language, model selection

## How It Works

### Recording Flow

1. Press **Ctrl+Alt+F4** (or click the floating widget)
2. Speak into your microphone
3. Press the hotkey again (or click) to stop
4. Audio is transcribed by Whisper
5. Text is automatically pasted into your active application

### Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Hotkey    │───▶│    Audio     │───▶│   Recognition   │
│   (pynput)  │    │  (sounddev)  │    │ (faster-whisper)│
└─────────────┘    └──────────────┘    └────────┬────────┘
                                                │
┌─────────────┐    ┌──────────────┐    ┌────────▼────────┐
│   Inject    │◀───│    Cleanup   │◀───│   Transcribed   │
│  (Ctrl+V)   │    │    (regex)   │    │      Text       │
└─────────────┘    └──────────────┘    └─────────────────┘
```

## Speech Recognition Engines

### Local Engine (Default) - Faster-Whisper

| Aspect | Details |
|--------|---------|
| **Library** | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) |
| **Model** | OpenAI Whisper (CTranslate2 optimized) |
| **Runs On** | Your CPU or GPU (auto-detected) |
| **Internet** | Only for initial model download (~75MB-3GB) |
| **Privacy** | Full - audio never leaves your machine |
| **Cost** | Free |
| **Speed** | ~2-5 seconds for short clips on modern hardware |

**Available Models:**
| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| tiny | 75MB | Fastest | Basic |
| base | 150MB | Fast | Good |
| small | 500MB | Medium | Better |
| medium | 1.5GB | Slow | Great |
| large-v3 | 3GB | Slowest | Best |

### API Engine (Optional) - OpenAI

| Aspect | Details |
|--------|---------|
| **Service** | OpenAI Whisper API |
| **Model** | whisper-1 (hosted by OpenAI) |
| **Internet** | Required for every transcription |
| **Privacy** | Audio sent to OpenAI servers |
| **Cost** | $0.006 per minute of audio |
| **Speed** | ~1-3 seconds (network dependent) |

## Installation

### Prerequisites

- Windows 10/11
- Python 3.10 or later (3.12 recommended)
- Microphone

### Setup

```bash
# Clone or download the project
cd Whisper-Voice-Input

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate

py -3.12 -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python -m src.main
```

### First Run

On first launch:
1. The app downloads the Whisper model (~150MB for "base")
2. A floating widget appears in the top-right corner
3. A system tray icon appears
4. Press **Ctrl+Alt+F4** to test!

## Running as a Desktop App

### Option 1: VBS Launcher (No Console)

Create `run.vbs`:
```vbs
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw -m src.main", 0, False
```

### Option 2: Standalone Executable

```bash
pip install pyinstaller
pyinstaller --name "Whisper Voice Input" --windowed --onefile src/main.py
```

Creates `dist/Whisper Voice Input.exe`

### Option 3: Start with Windows

1. Open Settings in the app
2. Enable "Start with Windows"
3. Or manually add a shortcut to `shell:startup`

## Configuration

Access settings via:
- Right-click system tray → Settings
- Or keyboard shortcut (configurable)

### Settings Options

| Setting | Options |
|---------|---------|
| Hotkey | Any key + Ctrl/Shift/Alt modifiers |
| Widget Size | Compact (40px), Medium (60px), Large (80px) |
| Engine | Local (Faster-Whisper) or API (OpenAI) |
| Model | tiny, base, small, medium, large-v3 |
| Language | English (Auto), US, UK, South Africa |
| API Key | Your OpenAI API key (for API engine) |

Settings stored in: `%AppData%\Whisper Voice Input\settings.json`

## Privacy & Security

### Local Engine (Default)
- **100% offline** after initial model download
- Audio processed entirely on your machine
- No data transmitted anywhere
- Model files cached in HuggingFace cache directory

### API Engine
- Audio files sent to OpenAI servers
- Subject to [OpenAI's privacy policy](https://openai.com/policies/privacy-policy)
- API key stored locally (not encrypted)

### Text Injection
- Uses system clipboard temporarily
- Simulates Ctrl+V keystroke
- May briefly overwrite clipboard contents

## Internet Connectivity

| Action | Internet Required? |
|--------|-------------------|
| First run (model download) | Yes |
| Local transcription | No |
| API transcription | Yes |
| Checking for updates | No (not implemented) |
| Sending telemetry | No (none collected) |

## Licensing

### This Application
MIT License - free for personal and commercial use.

### Dependencies

| Library | License | Notes |
|---------|---------|-------|
| faster-whisper | MIT | CTranslate2 Whisper implementation |
| OpenAI Whisper | MIT | Original model by OpenAI |
| PyQt6 | GPL v3 | Qt framework bindings |
| pynput | LGPL v3 | Keyboard/mouse input |
| sounddevice | MIT | Audio I/O |
| numpy/scipy | BSD | Numerical computing |
| openai | MIT | OpenAI API client |

**Note**: PyQt6 uses GPL v3. For commercial distribution, consider Qt commercial license or switch to PySide6 (LGPL).

### Whisper Model License
The Whisper models are released by OpenAI under the MIT License. They were trained on 680,000 hours of web audio data.

## Troubleshooting

### "No module named 'faster_whisper'"
```bash
pip install faster-whisper
```

### Model download fails
- Check internet connection
- Try: `pip install huggingface_hub && python -c "from huggingface_hub import login; login()"`

### Hotkey not working
- Check for conflicts with other apps
- Try a different key combination
- Run as Administrator (for some apps)

### No audio detected
- Check microphone permissions in Windows Settings
- Verify correct audio device in Settings
- Test microphone in another app

### Text not pasting
- Some apps block simulated keystrokes
- Try clicking in the target app first
- Check clipboard permissions

## Development

### Project Structure

```
src/
├── main.py           # Entry point
├── app.py            # Main controller
├── config/           # Settings & constants
├── audio/            # Recording & processing
├── recognition/      # Whisper engines
├── input/            # Hotkey & text injection
└── ui/               # PyQt6 interface
```

### Adding Features

See `CLAUDE.md` for developer documentation.

## Credits

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition model
- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) - Optimized implementation
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - UI framework

## Contributing

Contributions welcome! Please open an issue first to discuss changes.

## Changelog

### v1.0.0
- Initial release
- Local and API speech recognition
- Floating widget with audio-reactive animations
- System tray integration
- Global hotkey support
- Text cleanup and injection
