"""Application constants."""

APP_NAME = "Whisper Voice Input"
APP_VERSION = "1.0.0"
APP_AUTHOR = "WhisperVoiceInput"

# Default hotkey (Ctrl+Shift+Space)
DEFAULT_HOTKEY = {"ctrl": True, "shift": True, "alt": False, "key": "space"}

# Audio settings
SAMPLE_RATE = 16000  # Whisper expects 16kHz
CHANNELS = 1  # Mono audio

# Whisper model options
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
DEFAULT_MODEL = "base"

# Supported languages (out of box)
SUPPORTED_LANGUAGES = {
    "en": "English (Auto-detect)",
    "en-US": "English (US)",
    "en-GB": "English (UK)",
    "en-ZA": "English (South Africa)",
}
DEFAULT_LANGUAGE = "en"

# Recognition engines
ENGINE_LOCAL = "local"
ENGINE_API = "api"
DEFAULT_ENGINE = ENGINE_LOCAL

# UI constants - Circular widget
WIDGET_SIZES = {
    "compact": 60,
    "medium": 80,
    "large": 100,
}
DEFAULT_WIDGET_SIZE = "compact"
WIDGET_OPACITY = 0.95

# Widget colors (matched to _light PNG icons)
COLOR_BACKGROUND = "#0d1f2d"  # Dark teal blue
COLOR_IDLE = "#8fa3b8"        # Light grey-blue for idle/ready
COLOR_RECORDING = "#00bfff"   # Bright cyan-blue for recording
COLOR_PROCESSING = "#ffcc00"  # Bright yellow-orange for processing
COLOR_ERROR = "#ff4466"       # Bright coral-red for errors

# State constants
STATE_IDLE = "idle"
STATE_RECORDING = "recording"
STATE_PROCESSING = "processing"
STATE_ERROR = "error"

# Filler words to remove
FILLER_WORDS = [
    "um", "uh", "er", "ah", "like", "you know", "i mean",
    "basically", "actually", "literally", "so", "well",
]

# Voice command definitions
COMMAND_DEFINITIONS = {
    "delete that": {
        "action": "delete_last",
        "description": "Remove the last dictated segment"
    },
    "undo": {
        "action": "undo",
        "description": "Reverse the last command or dictation action"
    },
    "new line": {
        "action": "insert_newline",
        "description": "Insert line break at cursor position"
    },
}

# Spoken punctuation word-to-symbol mapping
PUNCTUATION_WORDS = {
    "period": ".",
    "comma": ",",
    "question mark": "?",
    "exclamation mark": "!",
    "exclamation point": "!",
    "colon": ":",
    "semicolon": ";",
    "dash": "—",
}

# Command detection threshold (fuzzy matching score 0-100)
COMMAND_THRESHOLD = 80
