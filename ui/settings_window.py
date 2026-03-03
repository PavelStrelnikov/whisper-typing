import customtkinter as ctk
import keyboard
import logging
from typing import Optional, Callable

from config.settings import AppSettings, STTProvider, ComputeType
from config.constants import (
    SUPPORTED_LANGUAGES,
    LOCAL_MODEL_SIZES,
    MOUSE_BUTTONS,
    TRIGGER_TYPE_KEYBOARD,
    TRIGGER_TYPE_MOUSE,
)
from core.audio_recorder import AudioRecorder

logger = logging.getLogger(__name__)

# Colors
CARD_BG = "#1e1e2e"
SECTION_BG = "#272740"
ACCENT = "#6c5ce7"
ACCENT_HOVER = "#5a4bd1"
DANGER = "#e74c3c"
DANGER_HOVER = "#c0392b"
TEXT_DIM = "#888899"
TEXT_BRIGHT = "#e0e0e0"
BORDER = "#3a3a5c"


def _make_card(parent, **kwargs):
    """Create a styled card frame."""
    return ctk.CTkFrame(
        parent,
        corner_radius=12,
        fg_color=SECTION_BG,
        border_width=1,
        border_color=BORDER,
        **kwargs,
    )


class SettingsWindow:
    """Modern settings dialog window."""

    def __init__(
        self,
        parent: ctk.CTk,
        settings: AppSettings,
        on_save: Optional[Callable[[AppSettings], None]] = None,
    ):
        self.settings = settings
        self.on_save = on_save
        self._window: Optional[ctk.CTkToplevel] = None
        self._parent = parent

    def show(self):
        if self._window is not None and self._window.winfo_exists():
            self._window.focus()
            return

        self._window = ctk.CTkToplevel(self._parent)
        self._window.title("WhisperTyping — Settings")
        self._window.geometry("500x660")
        self._window.resizable(False, True)
        self._window.configure(fg_color=CARD_BG)
        self._window.grab_set()

        # Header
        header = ctk.CTkFrame(self._window, fg_color=CARD_BG)
        header.pack(fill="x", padx=20, pady=(16, 4))
        ctk.CTkLabel(
            header, text="Settings",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=TEXT_BRIGHT,
        ).pack(side="left")

        # Scrollable content
        scroll = ctk.CTkScrollableFrame(
            self._window, fg_color=CARD_BG,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=ACCENT,
        )
        scroll.pack(fill="both", expand=True, padx=14, pady=(4, 0))

        # ─── STT Provider ────────────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)

        self._section_label(card, "Speech Recognition")

        self._provider_var = ctk.StringVar(value=self.settings.stt_provider)
        seg = ctk.CTkSegmentedButton(
            card, values=["local", "cloud"],
            variable=self._provider_var,
            command=lambda _: self._on_provider_change(),
            font=ctk.CTkFont(size=13),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
        )
        seg.pack(fill="x", padx=14, pady=(0, 10))

        # Local sub-card
        self._local_frame = ctk.CTkFrame(card, fg_color="transparent")

        row = ctk.CTkFrame(self._local_frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row, text="Model", text_color=TEXT_DIM, width=90, anchor="w").pack(side="left")
        self._model_size_var = ctk.StringVar(value=self.settings.local_model_size)
        ctk.CTkOptionMenu(
            row, variable=self._model_size_var, values=LOCAL_MODEL_SIZES,
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")

        row = ctk.CTkFrame(self._local_frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row, text="Device", text_color=TEXT_DIM, width=90, anchor="w").pack(side="left")
        self._device_var = ctk.StringVar(value=self.settings.device)
        ctk.CTkOptionMenu(
            row, variable=self._device_var, values=["cuda", "cpu"],
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")

        row = ctk.CTkFrame(self._local_frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(3, 10))
        ctk.CTkLabel(row, text="Precision", text_color=TEXT_DIM, width=90, anchor="w").pack(side="left")
        self._compute_var = ctk.StringVar(value=self.settings.compute_type)
        ctk.CTkOptionMenu(
            row, variable=self._compute_var,
            values=[ct.value for ct in ComputeType],
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")

        # Cloud sub-card
        self._cloud_frame = ctk.CTkFrame(card, fg_color="transparent")

        row = ctk.CTkFrame(self._cloud_frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row, text="API Key", text_color=TEXT_DIM, width=90, anchor="w").pack(side="left")
        self._api_key_var = ctk.StringVar(value=self.settings.openai_api_key)
        ctk.CTkEntry(
            row, textvariable=self._api_key_var, show="*",
            fg_color=CARD_BG, border_color=BORDER, width=200,
        ).pack(side="right")

        row = ctk.CTkFrame(self._cloud_frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(3, 10))
        ctk.CTkLabel(row, text="Model", text_color=TEXT_DIM, width=90, anchor="w").pack(side="left")
        self._cloud_model_var = ctk.StringVar(value=self.settings.openai_model)
        ctk.CTkOptionMenu(
            row, variable=self._cloud_model_var, values=["whisper-1"],
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")

        self._on_provider_change()

        # ─── Language ────────────────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)

        self._section_label(card, "Language")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 10))
        self._lang_var = ctk.StringVar(value=self.settings.language)
        for code, display in SUPPORTED_LANGUAGES.items():
            ctk.CTkRadioButton(
                row, text=display, variable=self._lang_var, value=code,
                font=ctk.CTkFont(size=13),
                fg_color=ACCENT, hover_color=ACCENT_HOVER,
            ).pack(side="left", padx=(0, 14))

        # ─── Microphone ─────────────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)

        self._section_label(card, "Microphone")

        devices = AudioRecorder.list_devices()
        device_names = ["System Default"] + [d["name"] for d in devices]
        device_indices = [-1] + [d["index"] for d in devices]
        self._device_map = dict(zip(device_names, device_indices))

        current_device = "System Default"
        for name, idx in self._device_map.items():
            if idx == self.settings.microphone_device_index:
                current_device = name
                break

        self._mic_var = ctk.StringVar(value=current_device)
        ctk.CTkOptionMenu(
            card, variable=self._mic_var, values=device_names,
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
        ).pack(fill="x", padx=14, pady=(0, 10))

        # ─── Trigger ─────────────────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)

        self._section_label(card, "Trigger")

        self._trigger_type_var = ctk.StringVar(value=self.settings.trigger_type)
        seg = ctk.CTkSegmentedButton(
            card, values=[TRIGGER_TYPE_KEYBOARD, TRIGGER_TYPE_MOUSE],
            variable=self._trigger_type_var,
            command=lambda _: self._on_trigger_type_change(),
            font=ctk.CTkFont(size=13),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
        )
        seg.pack(fill="x", padx=14, pady=(0, 8))

        # Keyboard trigger
        self._kb_frame = ctk.CTkFrame(card, fg_color="transparent")

        self._hotkey_var = ctk.StringVar(value=self.settings.trigger_key)
        self._hotkey_recording = False

        row = ctk.CTkFrame(self._kb_frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=3)

        ctk.CTkLabel(row, text="Hotkey", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")

        self._hotkey_display = ctk.CTkLabel(
            row, text=self.settings.trigger_key,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT, anchor="w",
        )
        self._hotkey_display.pack(side="left", padx=(4, 10))

        self._hotkey_btn = ctk.CTkButton(
            row, text="Record", width=80, height=28,
            font=ctk.CTkFont(size=12),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._start_hotkey_recording,
        )
        self._hotkey_btn.pack(side="right")

        # Mouse trigger
        self._mouse_frame = ctk.CTkFrame(card, fg_color="transparent")

        row = ctk.CTkFrame(self._mouse_frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row, text="Button", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")
        self._mouse_btn_var = ctk.StringVar(value=self.settings.trigger_mouse_button)
        ctk.CTkOptionMenu(
            row, variable=self._mouse_btn_var,
            values=list(MOUSE_BUTTONS.keys()),
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")

        self._on_trigger_type_change()

        # Mode
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(8, 10))
        ctk.CTkLabel(row, text="Mode", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")
        self._mode_var = ctk.StringVar(value=self.settings.trigger_mode)
        ctk.CTkSegmentedButton(
            row, values=["push_to_talk", "toggle"],
            variable=self._mode_var,
            font=ctk.CTkFont(size=12),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
        ).pack(side="right")

        # ─── Text Injection ──────────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)

        self._section_label(card, "Text Injection")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row, text="Method", text_color=TEXT_DIM, width=90, anchor="w").pack(side="left")
        self._injection_var = ctk.StringVar(value=self.settings.injection_method)
        ctk.CTkOptionMenu(
            row, variable=self._injection_var,
            values=["clipboard", "sendinput", "streaming"],
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")

        self._restore_clip_var = ctk.BooleanVar(value=self.settings.restore_clipboard)
        ctk.CTkCheckBox(
            card, text="Restore clipboard after paste",
            variable=self._restore_clip_var,
            font=ctk.CTkFont(size=13),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(anchor="w", padx=14, pady=3)

        self._trailing_space_var = ctk.BooleanVar(value=self.settings.add_trailing_space)
        ctk.CTkCheckBox(
            card, text="Add trailing space",
            variable=self._trailing_space_var,
            font=ctk.CTkFont(size=13),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(anchor="w", padx=14, pady=(3, 10))

        # ─── Text Normalization ──────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)

        self._section_label(card, "Text Normalization (LLM)")

        self._norm_enabled_var = ctk.BooleanVar(value=self.settings.normalize_trigger_enabled)
        ctk.CTkCheckBox(
            card, text="Enable normalize trigger (second hotkey)",
            variable=self._norm_enabled_var,
            font=ctk.CTkFont(size=13),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(anchor="w", padx=14, pady=(0, 6))

        # Normalize trigger type
        self._norm_trigger_type_var = ctk.StringVar(value=self.settings.normalize_trigger_type)
        ctk.CTkSegmentedButton(
            card, values=[TRIGGER_TYPE_KEYBOARD, TRIGGER_TYPE_MOUSE],
            variable=self._norm_trigger_type_var,
            command=lambda _: self._on_norm_trigger_type_change(),
            font=ctk.CTkFont(size=12),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
        ).pack(fill="x", padx=14, pady=(0, 6))

        # Normalize keyboard trigger
        self._norm_kb_frame = ctk.CTkFrame(card, fg_color="transparent")

        self._norm_hotkey_var = ctk.StringVar(value=self.settings.normalize_trigger_key)
        self._norm_hotkey_recording = False

        row = ctk.CTkFrame(self._norm_kb_frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row, text="Hotkey", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")

        self._norm_hotkey_display = ctk.CTkLabel(
            row, text=self.settings.normalize_trigger_key,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT, anchor="w",
        )
        self._norm_hotkey_display.pack(side="left", padx=(4, 10))

        self._norm_hotkey_btn = ctk.CTkButton(
            row, text="Record", width=80, height=28,
            font=ctk.CTkFont(size=12),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._start_norm_hotkey_recording,
        )
        self._norm_hotkey_btn.pack(side="right")

        # Normalize mouse trigger
        self._norm_mouse_frame = ctk.CTkFrame(card, fg_color="transparent")

        row = ctk.CTkFrame(self._norm_mouse_frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row, text="Button", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")
        self._norm_mouse_btn_var = ctk.StringVar(value=self.settings.normalize_trigger_mouse_button)
        ctk.CTkOptionMenu(
            row, variable=self._norm_mouse_btn_var,
            values=list(MOUSE_BUTTONS.keys()),
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")

        self._on_norm_trigger_type_change()

        # Normalize mode
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(6, 8))
        ctk.CTkLabel(row, text="Mode", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")
        self._norm_mode_var = ctk.StringVar(value=self.settings.normalize_trigger_mode)
        ctk.CTkSegmentedButton(
            row, values=["push_to_talk", "toggle"],
            variable=self._norm_mode_var,
            font=ctk.CTkFont(size=12),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
        ).pack(side="right")

        # LLM Provider
        self._section_label(card, "LLM Provider")

        self._llm_provider_var = ctk.StringVar(value=self.settings.normalize_llm_provider)
        ctk.CTkSegmentedButton(
            card, values=["openai", "gemini"],
            variable=self._llm_provider_var,
            command=lambda _: self._on_llm_provider_change(),
            font=ctk.CTkFont(size=13),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
        ).pack(fill="x", padx=14, pady=(0, 6))

        # OpenAI settings
        self._llm_openai_frame = ctk.CTkFrame(card, fg_color="transparent")

        row = ctk.CTkFrame(self._llm_openai_frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row, text="API Key", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")
        self._llm_openai_key_var = ctk.StringVar(value=self.settings.openai_api_key)
        ctk.CTkEntry(
            row, textvariable=self._llm_openai_key_var, show="*",
            fg_color=CARD_BG, border_color=BORDER, width=200,
        ).pack(side="right")

        row = ctk.CTkFrame(self._llm_openai_frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row, text="Model", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")
        self._llm_model_var = ctk.StringVar(value=self.settings.normalize_llm_model)
        ctk.CTkOptionMenu(
            row, variable=self._llm_model_var,
            values=["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1-nano"],
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")

        # Gemini settings
        self._llm_gemini_frame = ctk.CTkFrame(card, fg_color="transparent")

        row = ctk.CTkFrame(self._llm_gemini_frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row, text="API Key", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")
        self._gemini_key_var = ctk.StringVar(value=self.settings.gemini_api_key)
        ctk.CTkEntry(
            row, textvariable=self._gemini_key_var, show="*",
            fg_color=CARD_BG, border_color=BORDER, width=200,
        ).pack(side="right")

        self._on_llm_provider_change()

        # ─── Application ─────────────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)

        self._section_label(card, "Application")

        self._autostart_var = ctk.BooleanVar(value=self.settings.auto_start_with_windows)
        ctk.CTkCheckBox(
            card, text="Start with Windows",
            variable=self._autostart_var,
            font=ctk.CTkFont(size=13),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(anchor="w", padx=14, pady=(0, 10))

        # ─── Action buttons ──────────────────────
        btn_frame = ctk.CTkFrame(self._window, fg_color=CARD_BG)
        btn_frame.pack(fill="x", padx=20, pady=(8, 16))

        ctk.CTkButton(
            btn_frame, text="Save", command=self._save,
            width=110, height=36,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            corner_radius=10,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_frame, text="Cancel", command=self._cancel,
            width=110, height=36,
            font=ctk.CTkFont(size=14),
            fg_color="transparent", hover_color=SECTION_BG,
            border_width=1, border_color=BORDER,
            corner_radius=10,
        ).pack(side="right")

    # ── Helpers ───────────────────────────────────

    def _section_label(self, parent, text: str):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=TEXT_BRIGHT,
        ).pack(anchor="w", padx=14, pady=(10, 6))

    def _on_provider_change(self):
        if self._provider_var.get() == "local":
            self._cloud_frame.pack_forget()
            self._local_frame.pack(fill="x", after=self._local_frame.master.winfo_children()[1])
        else:
            self._local_frame.pack_forget()
            self._cloud_frame.pack(fill="x", after=self._cloud_frame.master.winfo_children()[1])

    def _on_trigger_type_change(self):
        if self._trigger_type_var.get() == TRIGGER_TYPE_KEYBOARD:
            self._mouse_frame.pack_forget()
            self._kb_frame.pack(fill="x", pady=2)
        else:
            self._kb_frame.pack_forget()
            self._mouse_frame.pack(fill="x", pady=2)

    def _on_norm_trigger_type_change(self):
        if self._norm_trigger_type_var.get() == TRIGGER_TYPE_KEYBOARD:
            self._norm_mouse_frame.pack_forget()
            self._norm_kb_frame.pack(fill="x", pady=2)
        else:
            self._norm_kb_frame.pack_forget()
            self._norm_mouse_frame.pack(fill="x", pady=2)

    def _on_llm_provider_change(self):
        if self._llm_provider_var.get() == "openai":
            self._llm_gemini_frame.pack_forget()
            self._llm_openai_frame.pack(fill="x", pady=2)
        else:
            self._llm_openai_frame.pack_forget()
            self._llm_gemini_frame.pack(fill="x", pady=2)

    def _start_hotkey_recording(self):
        if self._hotkey_recording:
            return
        self._hotkey_recording = True
        self._hotkey_btn.configure(text="Press...", fg_color=DANGER)
        self._hotkey_display.configure(text="Waiting...", text_color=DANGER)

        def _on_key(event):
            if event.event_type != "down":
                return
            parts = []
            for mod in ("ctrl", "shift", "alt"):
                if keyboard.is_pressed(mod):
                    parts.append(mod)
            name = event.name.lower()
            if name not in ("ctrl", "shift", "alt", "left ctrl", "right ctrl",
                            "left shift", "right shift", "left alt", "right alt"):
                parts.append(name)
            if not parts:
                return

            combo = "+".join(parts)
            keyboard.unhook(hook)
            self._hotkey_recording = False
            self._hotkey_var.set(combo)

            def _update_ui():
                self._hotkey_display.configure(text=combo, text_color=ACCENT)
                self._hotkey_btn.configure(text="Record", fg_color=ACCENT)
            if self._window and self._window.winfo_exists():
                self._window.after(0, _update_ui)

        hook = keyboard.hook(_on_key)

    def _start_norm_hotkey_recording(self):
        if self._norm_hotkey_recording:
            return
        self._norm_hotkey_recording = True
        self._norm_hotkey_btn.configure(text="Press...", fg_color=DANGER)
        self._norm_hotkey_display.configure(text="Waiting...", text_color=DANGER)

        def _on_key(event):
            if event.event_type != "down":
                return
            parts = []
            for mod in ("ctrl", "shift", "alt"):
                if keyboard.is_pressed(mod):
                    parts.append(mod)
            name = event.name.lower()
            if name not in ("ctrl", "shift", "alt", "left ctrl", "right ctrl",
                            "left shift", "right shift", "left alt", "right alt"):
                parts.append(name)
            if not parts:
                return

            combo = "+".join(parts)
            keyboard.unhook(hook)
            self._norm_hotkey_recording = False
            self._norm_hotkey_var.set(combo)

            def _update_ui():
                self._norm_hotkey_display.configure(text=combo, text_color=ACCENT)
                self._norm_hotkey_btn.configure(text="Record", fg_color=ACCENT)
            if self._window and self._window.winfo_exists():
                self._window.after(0, _update_ui)

        hook = keyboard.hook(_on_key)

    def _save(self):
        # Speech recognition
        self.settings.stt_provider = self._provider_var.get()
        self.settings.local_model_size = self._model_size_var.get()
        self.settings.device = self._device_var.get()
        self.settings.compute_type = self._compute_var.get()
        self.settings.openai_api_key = self._api_key_var.get()
        self.settings.openai_model = self._cloud_model_var.get()
        self.settings.language = self._lang_var.get()
        self.settings.microphone_device_index = self._device_map.get(
            self._mic_var.get(), -1
        )

        # Raw trigger
        self.settings.trigger_type = self._trigger_type_var.get()
        self.settings.trigger_key = self._hotkey_var.get()
        self.settings.trigger_mouse_button = self._mouse_btn_var.get()
        self.settings.trigger_mode = self._mode_var.get()

        # Text injection
        self.settings.injection_method = self._injection_var.get()
        self.settings.restore_clipboard = self._restore_clip_var.get()
        self.settings.add_trailing_space = self._trailing_space_var.get()

        # Normalize trigger + LLM
        self.settings.normalize_trigger_enabled = self._norm_enabled_var.get()
        self.settings.normalize_trigger_type = self._norm_trigger_type_var.get()
        self.settings.normalize_trigger_key = self._norm_hotkey_var.get()
        self.settings.normalize_trigger_mouse_button = self._norm_mouse_btn_var.get()
        self.settings.normalize_trigger_mode = self._norm_mode_var.get()
        self.settings.normalize_llm_provider = self._llm_provider_var.get()
        self.settings.normalize_llm_model = self._llm_model_var.get()
        self.settings.gemini_api_key = self._gemini_key_var.get()

        # Sync OpenAI API key — use whichever field has a value
        # LLM section key takes priority, fall back to Cloud STT key
        llm_key = self._llm_openai_key_var.get()
        cloud_key = self._api_key_var.get()
        if llm_key:
            self.settings.openai_api_key = llm_key
        elif cloud_key:
            self.settings.openai_api_key = cloud_key

        self.settings.auto_start_with_windows = self._autostart_var.get()
        self.settings.save()

        if self.on_save:
            self.on_save(self.settings)

        self._window.destroy()
        self._window = None
        logger.info("Settings saved")

    def _cancel(self):
        if self._hotkey_recording or self._norm_hotkey_recording:
            try:
                keyboard.unhook_all()
            except Exception:
                pass
            self._hotkey_recording = False
            self._norm_hotkey_recording = False
        if self._window:
            self._window.destroy()
            self._window = None
