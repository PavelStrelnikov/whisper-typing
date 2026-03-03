APP_NAME = "WhisperTyping"
APP_VERSION = "1.0.0"

SUPPORTED_LANGUAGES = {
    "auto": "Auto-detect",
    "ru": "Русский",
    "en": "English",
    "he": "עברית",
}

RTL_LANGUAGES = {"he", "ar"}

LOCAL_MODEL_SIZES = [
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3",
    "distil-large-v3",
]

AUDIO_CHANNELS = 1
DEFAULT_SAMPLE_RATE = 16000
MAX_RECORDING_SECONDS = 300
MIN_RECORDING_SECONDS = 0.3

# Trigger types for hotkey manager
TRIGGER_TYPE_KEYBOARD = "keyboard"
TRIGGER_TYPE_MOUSE = "mouse"

# Mouse button names (as used by the mouse library)
MOUSE_BUTTONS = {
    "middle": "Middle Click",
    "x": "Side Button (Back)",
    "x2": "Side Button (Forward)",
}
