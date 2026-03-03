import ctypes
import ctypes.wintypes as wintypes
import threading
import time
import logging

from config.settings import AppSettings, STTProvider
from config.constants import MIN_RECORDING_SECONDS
from core.audio_recorder import AudioRecorder
from core.stt_local import LocalSTTEngine
from core.stt_cloud import CloudSTTEngine
from core.text_injector import TextInjector
from core.hotkey_manager import HotkeyManager
from core.history import TranscriptionHistory, HistoryEntry
from core.text_normalizer import create_normalizer
from ui.floating_window import FloatingWindow, AppState
from ui.tray_icon import TrayIcon
from ui.settings_window import SettingsWindow
from ui.history_window import HistoryWindow

logger = logging.getLogger(__name__)

# Win32 API for foreground window tracking
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.BringWindowToTop.restype = wintypes.BOOL
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.ShowWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
SW_SHOW = 5


def force_foreground_window(hwnd):
    """Force a window to the foreground using AttachThreadInput.

    Windows blocks SetForegroundWindow from background processes.
    We attach our thread to the current foreground window's thread,
    gaining "foreground privileges" so SetForegroundWindow succeeds.
    No keystrokes are sent, so no menus get activated.
    """
    fg_hwnd = user32.GetForegroundWindow()
    if fg_hwnd == hwnd:
        return True

    our_thread = kernel32.GetCurrentThreadId()
    fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0

    attached = False
    try:
        # Attach to the FOREGROUND window's thread to inherit its privileges
        if fg_thread and our_thread != fg_thread:
            attached = bool(user32.AttachThreadInput(our_thread, fg_thread, True))

        user32.ShowWindow(hwnd, SW_SHOW)
        user32.BringWindowToTop(hwnd)
        result = user32.SetForegroundWindow(hwnd)

        if not result:
            logger.warning(f"SetForegroundWindow failed for hwnd={hwnd}")
        return bool(result)
    finally:
        if attached:
            user32.AttachThreadInput(our_thread, fg_thread, False)


class SingleInstance:
    """Prevent multiple app instances using a Windows named mutex."""

    def __init__(self, name="WhisperTyping_SingleInstance"):
        self._mutex = kernel32.CreateMutexW(None, False, name)
        self.already_running = (ctypes.GetLastError() == 183)  # ERROR_ALREADY_EXISTS

    def release(self):
        if self._mutex:
            kernel32.CloseHandle(self._mutex)
            self._mutex = None


kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


class Application:
    """Main application controller. Wires together all components."""

    def __init__(self):
        self._instance_lock = SingleInstance()
        if self._instance_lock.already_running:
            logger.warning("WhisperTyping is already running!")
            raise SystemExit(0)

        self.settings = AppSettings.load()
        self.recorder: AudioRecorder = None
        self.stt_engine = None
        self.text_injector: TextInjector = None
        self.hotkey_manager: HotkeyManager = None
        self.hotkey_manager_normalize: HotkeyManager = None
        self.text_normalizer = None
        self.floating_window: FloatingWindow = None
        self.tray_icon: TrayIcon = None
        self.history: TranscriptionHistory = TranscriptionHistory()
        self._target_hwnd = None  # Window to paste text into
        self._normalize_mode = False  # Set by which trigger fired

    def initialize(self):
        # Audio recorder
        self.recorder = AudioRecorder(
            sample_rate=self.settings.sample_rate,
            device_index=self.settings.microphone_device_index,
            on_level_update=self._on_audio_level,
        )

        # STT engine
        self._init_stt_engine()

        # Text normalizer (LLM)
        self._init_normalizer()

        # Text injector
        self.text_injector = TextInjector(
            method=self.settings.injection_method,
            restore_clipboard=self.settings.restore_clipboard,
            add_trailing_space=self.settings.add_trailing_space,
        )

        # Raw trigger (hotkey/mouse)
        self.hotkey_manager = HotkeyManager(
            trigger_type=self.settings.trigger_type,
            trigger_key=self.settings.trigger_key,
            trigger_mouse_button=self.settings.trigger_mouse_button,
            mode=self.settings.trigger_mode,
            on_recording_start=lambda: self._on_recording_start(normalize=False),
            on_recording_stop=lambda: self._on_recording_stop(),
        )

        # Normalize trigger (second hotkey/mouse)
        self.hotkey_manager_normalize = HotkeyManager(
            trigger_type=self.settings.normalize_trigger_type,
            trigger_key=self.settings.normalize_trigger_key,
            trigger_mouse_button=self.settings.normalize_trigger_mouse_button,
            mode=self.settings.normalize_trigger_mode,
            on_recording_start=lambda: self._on_recording_start(normalize=True),
            on_recording_stop=lambda: self._on_recording_stop(),
        )

        # Floating window
        self.floating_window = FloatingWindow(
            on_settings_click=self._open_settings,
            opacity=self.settings.window_opacity,
            always_on_top=self.settings.always_on_top,
        )

        # System tray
        self.tray_icon = TrayIcon(
            on_show_window=self._show_window,
            on_settings=self._open_settings,
            on_history=self._open_history,
            on_quit=self._quit,
        )

    def _init_stt_engine(self):
        if self.settings.stt_provider == STTProvider.LOCAL.value:
            self.stt_engine = LocalSTTEngine(
                model_size=self.settings.local_model_size,
                device=self.settings.device,
                compute_type=self.settings.compute_type,
            )
        else:
            self.stt_engine = CloudSTTEngine(
                api_key=self.settings.openai_api_key,
                model=self.settings.openai_model,
            )

    def _init_normalizer(self):
        self.text_normalizer = create_normalizer(
            provider=self.settings.normalize_llm_provider,
            openai_api_key=self.settings.openai_api_key,
            openai_model=self.settings.normalize_llm_model,
            gemini_api_key=self.settings.gemini_api_key,
        )

    def run(self):
        self.initialize()

        # Start tray icon (background thread)
        self.tray_icon.start()

        # Register triggers
        self.hotkey_manager.register()
        if self.settings.normalize_trigger_enabled:
            self.hotkey_manager_normalize.register()

        # Preload local model in background
        if self.settings.stt_provider == STTProvider.LOCAL.value:
            threading.Thread(target=self._preload_model, daemon=True).start()

        # Create and run floating window (main thread, blocking)
        self.floating_window.create()
        logger.info("WhisperTyping started. Waiting for input trigger...")

        # If not preloading a model, auto-hide the window after a few seconds
        if self.settings.stt_provider != STTProvider.LOCAL.value:
            self.floating_window.set_state(AppState.IDLE)

        self.floating_window.run()

    def _preload_model(self):
        try:
            self.floating_window.set_state(AppState.LOADING, "Loading model...")
            self.stt_engine.is_available()
            self.floating_window.set_state(AppState.IDLE)
            logger.info("Model preloaded successfully")
        except Exception as e:
            logger.error(f"Model preload failed: {e}")
            self.floating_window.set_state(AppState.ERROR, f"Model: {e}")

    def _on_audio_level(self, level: float):
        if self.floating_window:
            self.floating_window.update_audio_level(level)

    def _on_recording_start(self, normalize: bool = False):
        # Save the currently focused window BEFORE anything else
        self._target_hwnd = user32.GetForegroundWindow()
        self._normalize_mode = normalize
        mode_label = "normalize" if normalize else "raw"
        logger.info(f"Recording started [{mode_label}] (target window: {self._target_hwnd})")
        self.floating_window.set_state(AppState.RECORDING)
        self.tray_icon.update_icon("recording")
        try:
            if self.settings.injection_method == "streaming" and not normalize:
                self.recorder.start_recording(
                    on_chunk_ready=self._on_stream_chunk,
                    silence_ms=self.settings.silence_threshold_ms,
                )
            else:
                self.recorder.start_recording()
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            self.floating_window.set_state(AppState.ERROR, str(e))

    def _on_stream_chunk(self, audio_data: bytes):
        """Called by AudioRecorder for each streaming chunk while recording."""
        target = self._target_hwnd
        threading.Thread(
            target=self._transcribe_streaming_chunk,
            args=(audio_data, target),
            daemon=True,
        ).start()

    def _transcribe_streaming_chunk(self, audio_data: bytes, target_hwnd):
        """Transcribe and inject a streaming chunk without changing UI state."""
        try:
            language = self.settings.language
            if language == "auto":
                language = None
            result = self.stt_engine.transcribe(audio_data, language)
            if result.text:
                logger.info(f"Streaming chunk [{result.language}]: {result.text}")
                if target_hwnd:
                    force_foreground_window(target_hwnd)
                    time.sleep(0.2)
                self.text_injector.inject_text(result.text, is_rtl=result.is_rtl)
                self.history.add(HistoryEntry.now(
                    text=result.text,
                    language=result.language,
                    duration=result.duration_seconds,
                    processing_time=result.processing_time_seconds,
                ))
        except Exception as e:
            logger.error(f"Streaming chunk transcription failed: {e}")

    def _on_recording_stop(self):
        logger.info("Recording stopped")
        self.floating_window.set_state(AppState.PROCESSING)
        self.tray_icon.update_icon("processing")

        audio_data = self.recorder.stop_recording()
        if audio_data is None or len(audio_data) < 1000:
            logger.info("Recording too short, ignoring")
            self.floating_window.set_state(AppState.IDLE)
            self.tray_icon.update_icon("idle")
            return

        # Transcribe in background, pass the target window handle and mode
        target = self._target_hwnd
        normalize = self._normalize_mode
        threading.Thread(
            target=self._transcribe_and_inject,
            args=(audio_data, target, normalize),
            daemon=True,
        ).start()

    def _transcribe_and_inject(self, audio_data: bytes, target_hwnd, normalize: bool = False):
        try:
            language = self.settings.language
            if language == "auto":
                language = None

            result = self.stt_engine.transcribe(audio_data, language)

            if result.text:
                logger.info(
                    f"Transcription [{result.language}] "
                    f"({result.processing_time_seconds:.2f}s): "
                    f"{result.text}"
                )

                # Normalize text through LLM if requested
                final_text = result.text
                if normalize and self.text_normalizer:
                    self.floating_window.set_state(AppState.NORMALIZING)
                    try:
                        final_text = self.text_normalizer.normalize(
                            result.text, result.language
                        )
                        logger.info(f"Normalized: {final_text}")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Normalization failed: {e}, using raw text")
                        # Show user-friendly error for common issues
                        if "insufficient_quota" in error_msg or "429" in error_msg:
                            self.floating_window.set_state(
                                AppState.ERROR, "No API credits — check billing"
                            )
                        elif "401" in error_msg or "invalid_api_key" in error_msg:
                            self.floating_window.set_state(
                                AppState.ERROR, "Invalid API key"
                            )
                        # Fall back to raw text on LLM failure
                elif normalize and not self.text_normalizer:
                    logger.warning("Normalize requested but no LLM configured")
                    self.floating_window.set_state(
                        AppState.ERROR, "No LLM configured in Settings"
                    )

                # Restore focus to the target window before pasting
                if target_hwnd:
                    ok = force_foreground_window(target_hwnd)
                    time.sleep(0.2)
                    actual = user32.GetForegroundWindow()
                    logger.info(
                        f"Focus restore: ok={ok}, "
                        f"target={target_hwnd}, actual={actual}"
                    )
                    # Retry once if focus didn't switch
                    if actual != target_hwnd:
                        force_foreground_window(target_hwnd)
                        time.sleep(0.2)

                self.text_injector.inject_text(
                    final_text, is_rtl=result.is_rtl
                )

                # Save to history (save the final text, not raw)
                self.history.add(HistoryEntry.now(
                    text=final_text,
                    language=result.language,
                    duration=result.duration_seconds,
                    processing_time=result.processing_time_seconds,
                ))
            else:
                logger.warning("Empty transcription result")
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            self.floating_window.set_state(AppState.ERROR, str(e))
            return

        self.floating_window.set_state(AppState.IDLE)
        self.tray_icon.update_icon("idle")

    def _open_settings(self):
        if not self.floating_window or not self.floating_window._root:
            return

        def _show():
            sw = SettingsWindow(
                parent=self.floating_window._root,
                settings=self.settings,
                on_save=self._on_settings_saved,
            )
            sw.show()

        self.floating_window._root.after(0, _show)

    def _on_settings_saved(self, new_settings: AppSettings):
        logger.info("Applying new settings...")
        old_provider = self.settings.stt_provider
        old_model = self.settings.local_model_size
        self.settings = new_settings

        # Rebuild STT engine if provider or model changed
        if (
            new_settings.stt_provider != old_provider
            or new_settings.local_model_size != old_model
        ):
            self._init_stt_engine()
            if new_settings.stt_provider == STTProvider.LOCAL.value:
                threading.Thread(
                    target=self._preload_model, daemon=True
                ).start()

        # Rebuild normalizer
        self._init_normalizer()

        # Update recorder
        self.recorder.device_index = (
            new_settings.microphone_device_index
            if new_settings.microphone_device_index != -1
            else None
        )
        self.recorder.sample_rate = new_settings.sample_rate

        # Update text injector
        self.text_injector.method = new_settings.injection_method
        self.text_injector.restore_clipboard = new_settings.restore_clipboard
        self.text_injector.add_trailing_space = new_settings.add_trailing_space

        # Update raw trigger
        self.hotkey_manager.update_trigger(
            trigger_type=new_settings.trigger_type,
            trigger_key=new_settings.trigger_key,
            trigger_mouse_button=new_settings.trigger_mouse_button,
            mode=new_settings.trigger_mode,
        )

        # Update normalize trigger (update_trigger calls register() internally)
        if new_settings.normalize_trigger_enabled:
            self.hotkey_manager_normalize.update_trigger(
                trigger_type=new_settings.normalize_trigger_type,
                trigger_key=new_settings.normalize_trigger_key,
                trigger_mouse_button=new_settings.normalize_trigger_mouse_button,
                mode=new_settings.normalize_trigger_mode,
            )
        else:
            self.hotkey_manager_normalize.unregister()

        # Apply autostart
        AppSettings.set_autostart(new_settings.auto_start_with_windows)

        # Update floating window visibility and always-on-top
        if self.floating_window and self.floating_window._root:
            self.floating_window._root.wm_attributes(
                "-topmost", new_settings.always_on_top
            )
            if not new_settings.show_floating_window:
                self.floating_window._root.after(
                    0, self.floating_window._root.withdraw
                )

        logger.info("Settings applied")

    def _open_history(self):
        if not self.floating_window or not self.floating_window._root:
            return

        def _show():
            hw = HistoryWindow(
                parent=self.floating_window._root,
                history=self.history,
            )
            hw.show()

        self.floating_window._root.after(0, _show)

    def _show_window(self):
        if self.floating_window:
            self.floating_window.show()

    def _quit(self):
        logger.info("Application shutting down")
        try:
            self.hotkey_manager.unregister()
        except Exception:
            pass
        try:
            self.hotkey_manager_normalize.unregister()
        except Exception:
            pass
        try:
            self.recorder.cleanup()
        except Exception:
            pass
        try:
            self.tray_icon.stop()
        except Exception:
            pass
        try:
            self._instance_lock.release()
        except Exception:
            pass
        self.floating_window.quit()
