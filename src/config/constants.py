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
    "compact": 40,
    "medium": 60,
    "large": 80,
}
DEFAULT_WIDGET_SIZE = "compact"
WIDGET_OPACITY = 0.95

# Widget colors
COLOR_BACKGROUND = "#0d1f2d"  # Dark teal blue
COLOR_IDLE = "#6b7b8c"        # Grey-blue for idle/ready
COLOR_RECORDING = "#00a8ff"   # Bright blue for recording
COLOR_PROCESSING = "#ffb347"  # Warm amber for processing
COLOR_ERROR = "#e94560"       # Red for errors

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
