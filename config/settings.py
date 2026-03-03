from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
import json
import logging
import sys
import winreg

logger = logging.getLogger(__name__)


class STTProvider(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"


class Language(str, Enum):
    AUTO = "auto"
    RUSSIAN = "ru"
    ENGLISH = "en"
    HEBREW = "he"


class ComputeType(str, Enum):
    FLOAT16 = "float16"
    INT8_FLOAT16 = "int8_float16"
    INT8 = "int8"
    FLOAT32 = "float32"


@dataclass
class AppSettings:
    # STT Configuration
    stt_provider: str = STTProvider.LOCAL.value
    openai_api_key: str = ""
    openai_model: str = "whisper-1"
    local_model_size: str = "large-v3"
    compute_type: str = ComputeType.FLOAT16.value
    device: str = "cuda"

    # Language
    language: str = Language.AUTO.value

    # Audio
    microphone_device_index: int = -1  # -1 = system default
    sample_rate: int = 16000
    vad_enabled: bool = True
    silence_threshold_ms: int = 500

    # Trigger (hotkey or mouse button)
    trigger_type: str = "keyboard"  # "keyboard" or "mouse"
    trigger_key: str = "F9"  # keyboard key or combo
    trigger_mouse_button: str = "middle"  # middle, x, x2
    trigger_mode: str = "toggle"  # push_to_talk or toggle

    # Text Injection
    injection_method: str = "clipboard"  # clipboard, sendinput, or streaming
    restore_clipboard: bool = True
    add_trailing_space: bool = True
    streaming_chunk_interval: float = 3.0  # seconds between streaming chunks

    # Normalize trigger (second hotkey — transcribe + LLM cleanup)
    normalize_trigger_enabled: bool = True
    normalize_trigger_type: str = "keyboard"
    normalize_trigger_key: str = "F10"
    normalize_trigger_mouse_button: str = "x"
    normalize_trigger_mode: str = "toggle"

    # LLM for normalization
    normalize_llm_provider: str = "openai"  # "openai" or "gemini"
    normalize_llm_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""

    # UI
    always_on_top: bool = True
    start_minimized: bool = False
    show_floating_window: bool = True
    window_opacity: float = 0.9
    window_position_x: int = -1  # -1 = auto
    window_position_y: int = -1

    # Application
    auto_start_with_windows: bool = False
    log_level: str = "INFO"

    @staticmethod
    def set_autostart(enabled: bool):
        """Add or remove app from Windows startup registry."""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "WhisperTyping"
        # When running as PyInstaller exe — sys.executable is the .exe path
        exe_path = sys.executable
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path,
                0, winreg.KEY_SET_VALUE
            )
            if enabled:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            logger.info(f"Autostart {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            logger.error(f"Failed to set autostart: {e}")

    @staticmethod
    def config_dir() -> Path:
        appdata = Path.home() / "AppData" / "Roaming" / "WhisperTyping"
        appdata.mkdir(parents=True, exist_ok=True)
        return appdata

    @staticmethod
    def config_path() -> Path:
        return AppSettings.config_dir() / "settings.json"

    def save(self):
        data = asdict(self)
        # Don't persist the API key if empty
        with open(self.config_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Settings saved to {self.config_path()}")

    @classmethod
    def load(cls) -> "AppSettings":
        path = cls.config_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Merge with defaults for forward compatibility
                defaults = asdict(cls())
                defaults.update(data)
                return cls(**{
                    k: v for k, v in defaults.items()
                    if k in cls.__dataclass_fields__
                })
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to load settings: {e}, using defaults")
                return cls()
        return cls()
