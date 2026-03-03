import ctypes
import customtkinter as ctk
import logging
from enum import Enum
from typing import Optional, Callable

# Win32: Make window non-focusable (WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008

_user32 = ctypes.windll.user32
_user32.GetWindowLongW.restype = ctypes.c_long
_user32.SetWindowLongW.restype = ctypes.c_long

logger = logging.getLogger(__name__)


class AppState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    NORMALIZING = "normalizing"
    ERROR = "error"
    LOADING = "loading"


AUTO_HIDE_DELAY_MS = 3000  # Hide window after 3 seconds of idle
ERROR_HIDE_DELAY_MS = 5000  # Keep errors visible a bit longer


class FloatingWindow:
    """Small floating overlay window showing recording status."""

    def __init__(
        self,
        on_settings_click: Optional[Callable] = None,
        opacity: float = 0.9,
        always_on_top: bool = True,
    ):
        self.on_settings_click = on_settings_click
        self.opacity = opacity
        self.always_on_top = always_on_top

        self._root: Optional[ctk.CTk] = None
        self._state = AppState.IDLE
        self._status_label = None
        self._level_bar = None
        self._drag_data = {"x": 0, "y": 0}
        self._auto_hide_timer = None  # after() id for auto-hide
        self._pinned = False  # True = don't auto-hide

    def create(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._root = ctk.CTk()
        self._root.title("WhisperTyping")
        self._root.geometry("300x80")
        self._root.resizable(False, False)
        self._root.overrideredirect(True)
        self._root.wm_attributes("-topmost", self.always_on_top)
        self._root.wm_attributes("-alpha", self.opacity)

        # Make the window non-focusable so it doesn't steal focus from target apps
        self._root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(self._root.winfo_id())
        if not hwnd:
            hwnd = self._root.winfo_id()
        style = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        _user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE,
            style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST,
        )

        # Position at bottom-right of screen
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x = screen_w - 320
        y = screen_h - 130
        self._root.geometry(f"+{x}+{y}")

        # Make window draggable
        self._root.bind("<Button-1>", self._start_drag)
        self._root.bind("<B1-Motion>", self._on_drag)

        # Main frame
        frame = ctk.CTkFrame(self._root, corner_radius=12)
        frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Top row: status indicator + text
        top_frame = ctk.CTkFrame(frame, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=(8, 2))

        self._indicator = ctk.CTkLabel(
            top_frame, text="\u25cf", font=ctk.CTkFont(size=16),
            text_color="#4CAF50", width=20,
        )
        self._indicator.pack(side="left")

        self._status_label = ctk.CTkLabel(
            top_frame, text="Ready \u2014 Press hotkey to speak",
            font=ctk.CTkFont(size=13), anchor="w",
        )
        self._status_label.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # Bottom row: level meter + settings button
        bottom_frame = ctk.CTkFrame(frame, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=10, pady=(0, 8))

        self._level_bar = ctk.CTkProgressBar(
            bottom_frame, width=220, height=8,
            progress_color="#4CAF50",
        )
        self._level_bar.pack(side="left", fill="x", expand=True)
        self._level_bar.set(0)

        settings_btn = ctk.CTkButton(
            bottom_frame, text="\u2699", width=30, height=24,
            font=ctk.CTkFont(size=16),
            command=self._on_settings,
        )
        settings_btn.pack(side="right", padx=(8, 0))

        # Hide button (minimize to tray)
        close_btn = ctk.CTkButton(
            bottom_frame, text="\u2015", width=30, height=24,
            font=ctk.CTkFont(size=12),
            fg_color="transparent", hover_color="#555555",
            command=self._on_close,
        )
        close_btn.pack(side="right", padx=(4, 0))

        # Pin button (toggle auto-hide)
        self._pin_btn = ctk.CTkButton(
            bottom_frame, text="\U0001f4cc", width=30, height=24,
            font=ctk.CTkFont(size=12),
            fg_color="transparent", hover_color="#555555",
            command=self._toggle_pin,
        )
        self._pin_btn.pack(side="right", padx=(4, 0))

    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag(self, event):
        x = self._root.winfo_x() + event.x - self._drag_data["x"]
        y = self._root.winfo_y() + event.y - self._drag_data["y"]
        self._root.geometry(f"+{x}+{y}")

    def _toggle_pin(self):
        self._pinned = not self._pinned
        if self._pinned:
            self._cancel_auto_hide()
            self._pin_btn.configure(fg_color="#555555")
        else:
            self._pin_btn.configure(fg_color="transparent")
            # If currently idle, start auto-hide
            if self._state == AppState.IDLE:
                self._schedule_auto_hide()

    def _on_settings(self):
        if self.on_settings_click:
            self.on_settings_click()

    def _on_close(self):
        if self._root:
            self._pinned = False
            self._cancel_auto_hide()
            self._root.withdraw()

    def _cancel_auto_hide(self):
        """Cancel any pending auto-hide timer."""
        if self._auto_hide_timer is not None:
            self._root.after_cancel(self._auto_hide_timer)
            self._auto_hide_timer = None

    def _schedule_auto_hide(self, delay_ms: int = AUTO_HIDE_DELAY_MS):
        """Schedule the window to hide after delay_ms."""
        self._cancel_auto_hide()
        if not self._pinned:
            self._auto_hide_timer = self._root.after(delay_ms, self._auto_hide)

    def _auto_hide(self):
        """Hide the window (auto-hide timer fired)."""
        self._auto_hide_timer = None
        if self._root and self._state == AppState.IDLE:
            self._root.withdraw()
            logger.debug("Window auto-hidden")

    def set_state(self, state: AppState, detail: str = ""):
        def _update():
            self._state = state
            if state == AppState.IDLE:
                self._status_label.configure(
                    text="Ready \u2014 Press hotkey to speak",
                    text_color="white",
                )
                self._indicator.configure(text_color="#4CAF50")
                self._level_bar.configure(progress_color="#4CAF50")
                self._level_bar.set(0)
                # Auto-hide after a few seconds
                self._schedule_auto_hide()
            elif state == AppState.RECORDING:
                self._cancel_auto_hide()
                self._pinned = False
                self._pin_btn.configure(fg_color="transparent")
                self._root.deiconify()  # Show window when recording
                self._status_label.configure(
                    text="\ud83c\udfa4 Recording... Release to stop",
                    text_color="#FF4444",
                )
                self._indicator.configure(text_color="#FF4444")
                self._level_bar.configure(progress_color="#FF4444")
            elif state == AppState.PROCESSING:
                self._cancel_auto_hide()
                self._status_label.configure(
                    text="\u23f3 Transcribing...",
                    text_color="#FFAA00",
                )
                self._indicator.configure(text_color="#FFAA00")
                self._level_bar.configure(progress_color="#FFAA00")
                self._level_bar.set(0)
            elif state == AppState.NORMALIZING:
                self._cancel_auto_hide()
                self._status_label.configure(
                    text="\u2728 Polishing text...",
                    text_color="#6c5ce7",
                )
                self._indicator.configure(text_color="#6c5ce7")
                self._level_bar.configure(progress_color="#6c5ce7")
                self._level_bar.set(0)
            elif state == AppState.LOADING:
                self._cancel_auto_hide()
                msg = detail or "Loading model..."
                self._status_label.configure(
                    text=f"\u23f3 {msg}",
                    text_color="#64B5F6",
                )
                self._indicator.configure(text_color="#64B5F6")
            elif state == AppState.ERROR:
                self._cancel_auto_hide()
                self._root.deiconify()  # Show window on error
                self._status_label.configure(
                    text=f"\u26a0 {detail}" if detail else "\u26a0 Error",
                    text_color="#FF6666",
                )
                self._indicator.configure(text_color="#FF6666")
                # Auto-hide errors after longer delay
                self._schedule_auto_hide(ERROR_HIDE_DELAY_MS)

        if self._root:
            self._root.after(0, _update)

    def update_audio_level(self, level: float):
        if self._root and self._state == AppState.RECORDING:
            normalized = min(1.0, level * 10)
            self._root.after(0, lambda: self._level_bar.set(normalized))

    def show(self):
        """Show the window (e.g. from tray icon). Pins it so it won't auto-hide."""
        if self._root:
            def _show():
                self._pinned = True
                self._cancel_auto_hide()
                self._root.deiconify()
            self._root.after(0, _show)

    def run(self):
        if self._root:
            self._root.mainloop()

    def quit(self):
        if self._root:
            self._root.after(0, self._root.destroy)
