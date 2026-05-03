"""Application constants."""

APP_NAME = "Whisper Voice Input"
APP_VERSION = "1.0.1"
APP_AUTHOR = "WhisperVoiceInput"

# Default hotkey (Ctrl+Shift+Space)
DEFAULT_HOTKEY = {"ctrl": True, "shift": True, "alt": False, "key": "space"}
# Separate hotkey for command-only capture. Pressing this triggers a short
# recording where every utterance is interpreted as a command (no wake-word
# prefix needed). Ctrl+Shift+C chosen as a low-collision combo that doesn't
# clash with the universal Ctrl+C copy shortcut (Shift makes the difference).
DEFAULT_COMMAND_HOTKEY = {"ctrl": True, "shift": True, "alt": False, "key": "c"}

# Hotkey debounce (milliseconds) - prevents key bounce and rapid re-fire
HOTKEY_DEBOUNCE_MS = 500

# Transcription timeout (seconds) - prevents indefinite hang
TRANSCRIPTION_TIMEOUT_SECONDS = 120

# Audio settings
SAMPLE_RATE = 16000  # Whisper expects 16kHz
CHANNELS = 1  # Mono audio

# Whisper model options
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
DEFAULT_MODEL = "base"

# Supported languages
# "auto" = let Whisper auto-detect (unreliable on short audio)
# All other codes force the language explicitly to Whisper
SUPPORTED_LANGUAGES = {
    "auto": "Auto-detect",
    "en": "English",
    "af": "Afrikaans",
    "en-US": "English (US)",
    "en-GB": "English (UK)",
    "en-ZA": "English (South Africa)",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "pl": "Polish",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    "cs": "Czech",
    "ro": "Romanian",
    "uk": "Ukrainian",
    "el": "Greek",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
    "he": "Hebrew",
    "fa": "Persian",
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
# Command-mode capture: visually distinct from dictation RECORDING. Repurposes
# the orange mic identity that was previously only used during PROCESSING in
# batch mode (PROCESSING is now mostly vestigial once streaming is the default).
STATE_COMMAND = "command"

# Filler words to remove
FILLER_WORDS = [
    "um", "uh", "er", "ah", "like", "you know", "i mean",
    "basically", "actually", "literally", "so", "well",
]

# Wake-word prefix that disambiguates commands from dictation.
# Utterances starting with this word are routed to the command dispatcher;
# everything else is dictation. Eliminates fuzzy-match false positives.
COMMAND_WAKE_WORD = "command"

# Editor commands: spoken phrase → OS keystroke string (pyautogui.hotkey format).
# All entries are stateless, universal Windows shortcuts — they hand off to
# whatever editor is focused, so we never corrupt user state.
COMMAND_DEFINITIONS = {
    "undo":       {"keystroke": "ctrl+z",  "description": "Undo last edit"},
    "redo":       {"keystroke": "ctrl+y",  "description": "Redo last edit"},
    "save":       {"keystroke": "ctrl+s",  "description": "Save current document"},
    "select all": {"keystroke": "ctrl+a",  "description": "Select all"},
    "copy":       {"keystroke": "ctrl+c",  "description": "Copy selection"},
    "paste":      {"keystroke": "ctrl+v",  "description": "Paste"},
    "cut":        {"keystroke": "ctrl+x",  "description": "Cut selection"},
    "find":       {"keystroke": "ctrl+f",  "description": "Open find dialog"},
}

# Spoken punctuation/whitespace word-to-symbol mapping.
# Multi-word keys are matched first (longest-key-first) by the processor.
# These run before filler-word removal in the cleanup pipeline.
PUNCTUATION_WORDS = {
    "new paragraph": "\n\n",
    "new line": "\n",
    "exclamation mark": "!",
    "exclamation point": "!",
    "question mark": "?",
    "full stop": ".",
    "period": ".",
    "comma": ",",
    "colon": ":",
    "semicolon": ";",
    "dash": "—",
    "hyphen": "-",
    "apostrophe": "'",
    "quote": '"',
}

# Command detection threshold (fuzzy matching score 0-100).
# Used only to forgive minor mishearings of the command word itself
# ("undue" -> "undo"). Wake-word prefix already eliminates ambiguity,
# so this can be relatively lenient.
COMMAND_THRESHOLD = 65

# ── Streaming transcription tuning ─────────────────────────────────────────
# Used by StreamingTranscriber + app.py command-capture flow. Centralised so
# tuning happens in one place per the project's DRY rule.

# Length of the rolling audio window passed to Whisper each round.
# Longer = more context (better accuracy on long sentences) but heavier per-round
# CPU. 12s gives Whisper enough context to disambiguate while staying fast.
STREAM_WINDOW_SECONDS = 12.0

# How often a new transcription round runs. Each round pays the full
# transcribe-window cost, so this is the lower bound on commit latency.
STREAM_INTERVAL_SECONDS = 1.0

# Min silence (ms) before VAD fires a segment boundary in streaming mode.
# Shorter than the batch default (2000) so spoken-punctuation pauses are
# detected promptly during continuous dictation.
STREAM_VAD_MIN_SILENCE_MS = 500

# Whisper decoder parameters shared by transcribe() and transcribe_array().
# Centralising avoids drift between batch and streaming paths.
WHISPER_BEAM_SIZE = 5
WHISPER_BEST_OF = 5
WHISPER_TEMPERATURE = 0.0

# Settle delay before the FIRST streaming injection — gives the OS time to
# move focus to the saved HWND before pyautogui.hotkey('ctrl', 'v') runs.
STREAM_FOCUS_SETTLE_MS = 150

# ── VAD-driven session lifecycle ───────────────────────────────────────────
# Audio level threshold (normalised 0..1 RMS, same scale as the level callback)
# below which we treat the input as silence. Quiet built-in mics on default
# audio paths can produce normal speech in the 0.02..0.10 range, which is
# why this is set conservatively low. Picking a real headset or external mic
# in Settings → Audio gives much louder input and makes this threshold
# comfortable. The bar-strip cutoff is 0.02, so anything visible on the bars
# should now reliably register as "not silence" for VAD lifecycle decisions.
SILENCE_THRESHOLD = 0.015

# Streaming: how long of continuous silence before we pause Whisper rounds.
# Mic stays open, bar strip keeps tracking, but no transcription work runs.
# Resumes automatically on next loud sample. Helps avoid hallucinations on
# long silences (Whisper sometimes invents '[Music]' or repeats the last word).
STREAM_AUTO_PAUSE_SECONDS = 2.0

# Streaming: how long of continuous silence (counts pause time) before the
# session auto-deactivates and returns to idle. Prevents a forgotten session
# from running indefinitely if the user walks away.
STREAM_AUTO_STOP_SECONDS = 60.0

# Command capture: how long of silence AFTER speech was detected before we
# treat the utterance as complete and fire. Keeps the modality single-press —
# user says "save", silence triggers fire, no second hotkey needed.
COMMAND_AUTO_STOP_AFTER_SPEECH_SECONDS = 1.5

# Command capture: bail out if no speech is ever detected within this window.
# Covers the "accidentally pressed the hotkey" case.
COMMAND_NO_SPEECH_TIMEOUT_SECONDS = 8.0

# How often the silence-monitor poll timer ticks (ms). Smaller = snappier
# transitions but more wakeups; 200ms is imperceptible at human-speech timescales.
SILENCE_POLL_INTERVAL_MS = 200
