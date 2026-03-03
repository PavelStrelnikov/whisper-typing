import customtkinter as ctk
import keyboard
import logging
import os
from typing import Optional, Callable

_ICON_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico")

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
    """Modern tabbed settings dialog window."""

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

        # Hotkey recording state
        self._hotkey_recording = False
        self._norm_hotkey_recording = False

    def show(self):
        if self._window is not None and self._window.winfo_exists():
            self._window.focus()
            return

        self._window = ctk.CTkToplevel(self._parent)
        self._window.title("WhisperTyping — Settings")
        self._window.geometry("520x680")
        self._window.resizable(False, True)
        self._window.configure(fg_color=CARD_BG)
        self._window.grab_set()
        if os.path.exists(_ICON_PATH):
            self._window.after(100, lambda: self._window.iconbitmap(_ICON_PATH))

        # Header
        header = ctk.CTkFrame(self._window, fg_color=CARD_BG)
        header.pack(fill="x", padx=20, pady=(16, 6))
        ctk.CTkLabel(
            header, text="Settings",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=TEXT_BRIGHT,
        ).pack(side="left")

        # Tab view
        tabview = ctk.CTkTabview(
            self._window,
            fg_color=CARD_BG,
            segmented_button_fg_color=SECTION_BG,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_color=SECTION_BG,
            segmented_button_unselected_hover_color=BORDER,
            border_width=1,
            border_color=BORDER,
        )
        tabview.pack(fill="both", expand=True, padx=14, pady=(0, 0))

        for tab_name in ("Recognition", "Hotkeys", "Output", "App"):
            tabview.add(tab_name)

        self._build_recognition_tab(tabview.tab("Recognition"))
        self._build_hotkeys_tab(tabview.tab("Hotkeys"))
        self._build_output_tab(tabview.tab("Output"))
        self._build_app_tab(tabview.tab("App"))

        # Action buttons
        btn_frame = ctk.CTkFrame(self._window, fg_color=CARD_BG)
        btn_frame.pack(fill="x", padx=20, pady=(6, 16))

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

    # ── Tab builders ──────────────────────────────────────────────────────────

    def _build_recognition_tab(self, tab):
        scroll = self._tab_scroll(tab)

        # ── STT Provider ────────────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Speech Recognition")

        self._provider_var = ctk.StringVar(value=self.settings.stt_provider)
        ctk.CTkSegmentedButton(
            card, values=["local", "cloud"],
            variable=self._provider_var,
            command=lambda _: self._on_provider_change(),
            font=ctk.CTkFont(size=13),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
        ).pack(fill="x", padx=14, pady=(0, 4))
        self._desc(card, "Local = private, free, needs GPU/CPU. Cloud = OpenAI API, works on any computer.")

        # Local sub-card
        self._local_frame = ctk.CTkFrame(card, fg_color="transparent")

        row = self._row(self._local_frame)
        ctk.CTkLabel(row, text="Model", text_color=TEXT_DIM, width=90, anchor="w").pack(side="left")
        self._model_size_var = ctk.StringVar(value=self.settings.local_model_size)
        ctk.CTkOptionMenu(
            row, variable=self._model_size_var, values=LOCAL_MODEL_SIZES,
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")
        self._desc(self._local_frame, "Larger model = better accuracy, slower startup. large-v3 recommended for production.", padx=14)

        row = self._row(self._local_frame)
        ctk.CTkLabel(row, text="Device", text_color=TEXT_DIM, width=90, anchor="w").pack(side="left")
        self._device_var = ctk.StringVar(value=self.settings.device)
        ctk.CTkOptionMenu(
            row, variable=self._device_var, values=["cuda", "cpu"],
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")
        self._desc(self._local_frame, "Select cuda if you have an NVIDIA GPU for much faster transcription.", padx=14)

        row = self._row(self._local_frame, pady=(3, 6))
        ctk.CTkLabel(row, text="Precision", text_color=TEXT_DIM, width=90, anchor="w").pack(side="left")
        self._compute_var = ctk.StringVar(value=self.settings.compute_type)
        ctk.CTkOptionMenu(
            row, variable=self._compute_var,
            values=[ct.value for ct in ComputeType],
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")
        self._desc(self._local_frame, "float16 for GPU. int8/int8_float16 = faster, slightly less accurate.", padx=14)

        # Cloud sub-card
        self._cloud_frame = ctk.CTkFrame(card, fg_color="transparent")

        row = self._row(self._cloud_frame)
        ctk.CTkLabel(row, text="API Key", text_color=TEXT_DIM, width=90, anchor="w").pack(side="left")
        self._api_key_var = ctk.StringVar(value=self.settings.openai_api_key)
        ctk.CTkEntry(
            row, textvariable=self._api_key_var, show="*",
            fg_color=CARD_BG, border_color=BORDER, width=200,
        ).pack(side="right")
        self._desc(self._cloud_frame, "Your OpenAI API key (sk-…). Required for cloud transcription.", padx=14)

        row = self._row(self._cloud_frame, pady=(3, 6))
        ctk.CTkLabel(row, text="Model", text_color=TEXT_DIM, width=90, anchor="w").pack(side="left")
        self._cloud_model_var = ctk.StringVar(value=self.settings.openai_model)
        ctk.CTkOptionMenu(
            row, variable=self._cloud_model_var, values=["whisper-1"],
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")

        self._on_provider_change()

        # ── Language ─────────────────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Language")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 4))
        self._lang_var = ctk.StringVar(value=self.settings.language)
        for code, display in SUPPORTED_LANGUAGES.items():
            ctk.CTkRadioButton(
                row, text=display, variable=self._lang_var, value=code,
                font=ctk.CTkFont(size=13),
                fg_color=ACCENT, hover_color=ACCENT_HOVER,
            ).pack(side="left", padx=(0, 14))
        self._desc(card, "Auto-detect works well for most cases. Set explicitly if you record one language only.")

        # ── Microphone ───────────────────────────
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
        ).pack(fill="x", padx=14, pady=(0, 4))
        self._desc(card, "Audio input device. System Default works for most setups.")

    def _build_hotkeys_tab(self, tab):
        scroll = self._tab_scroll(tab)

        # ── Main Trigger ─────────────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Main Trigger")

        self._desc(card, "Keyboard combo or mouse button that starts/stops recording.")

        self._trigger_type_var = ctk.StringVar(value=self.settings.trigger_type)
        ctk.CTkSegmentedButton(
            card, values=[TRIGGER_TYPE_KEYBOARD, TRIGGER_TYPE_MOUSE],
            variable=self._trigger_type_var,
            command=lambda _: self._on_trigger_type_change(),
            font=ctk.CTkFont(size=13),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
        ).pack(fill="x", padx=14, pady=(4, 8))

        # Keyboard trigger frame
        self._kb_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._hotkey_var = ctk.StringVar(value=self.settings.trigger_key)
        self._hotkey_display, self._hotkey_btn = self._make_hotkey_recorder(
            self._kb_frame, self._hotkey_var,
            start_fn=self._start_hotkey_recording,
        )

        # Mouse trigger frame
        self._mouse_frame = ctk.CTkFrame(card, fg_color="transparent")
        row = self._row(self._mouse_frame, pady=(3, 6))
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
        row = self._row(card, pady=(4, 10))
        ctk.CTkLabel(row, text="Mode", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")
        self._mode_var = ctk.StringVar(value=self.settings.trigger_mode)
        ctk.CTkSegmentedButton(
            row, values=["push_to_talk", "toggle"],
            variable=self._mode_var,
            font=ctk.CTkFont(size=12),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
        ).pack(side="right")
        self._desc(card, "Push-to-talk: hold key while speaking. Toggle: press once to start, again to stop.")

        # ── Normalize Trigger ────────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Normalize Trigger")

        self._norm_enabled_var = ctk.BooleanVar(value=self.settings.normalize_trigger_enabled)
        ctk.CTkCheckBox(
            card, text="Enable normalize trigger",
            variable=self._norm_enabled_var,
            font=ctk.CTkFont(size=13),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(anchor="w", padx=14, pady=(0, 4))
        self._desc(card, "Second hotkey that transcribes AND runs AI cleanup on the text in one step.")

        self._norm_trigger_type_var = ctk.StringVar(value=self.settings.normalize_trigger_type)
        ctk.CTkSegmentedButton(
            card, values=[TRIGGER_TYPE_KEYBOARD, TRIGGER_TYPE_MOUSE],
            variable=self._norm_trigger_type_var,
            command=lambda _: self._on_norm_trigger_type_change(),
            font=ctk.CTkFont(size=12),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
        ).pack(fill="x", padx=14, pady=(4, 8))

        # Normalize keyboard frame
        self._norm_kb_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._norm_hotkey_var = ctk.StringVar(value=self.settings.normalize_trigger_key)
        self._norm_hotkey_display, self._norm_hotkey_btn = self._make_hotkey_recorder(
            self._norm_kb_frame, self._norm_hotkey_var,
            start_fn=self._start_norm_hotkey_recording,
        )

        # Normalize mouse frame
        self._norm_mouse_frame = ctk.CTkFrame(card, fg_color="transparent")
        row = self._row(self._norm_mouse_frame, pady=(3, 6))
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
        row = self._row(card, pady=(4, 10))
        ctk.CTkLabel(row, text="Mode", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")
        self._norm_mode_var = ctk.StringVar(value=self.settings.normalize_trigger_mode)
        ctk.CTkSegmentedButton(
            row, values=["push_to_talk", "toggle"],
            variable=self._norm_mode_var,
            font=ctk.CTkFont(size=12),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
        ).pack(side="right")

    def _build_output_tab(self, tab):
        scroll = self._tab_scroll(tab)

        # ── Text Injection ───────────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Text Injection")

        row = self._row(card)
        ctk.CTkLabel(row, text="Method", text_color=TEXT_DIM, width=90, anchor="w").pack(side="left")
        self._injection_var = ctk.StringVar(value=self.settings.injection_method)
        ctk.CTkOptionMenu(
            row, variable=self._injection_var,
            values=["clipboard", "sendinput", "streaming"],
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")
        self._desc(card, "Clipboard: most compatible. SendInput: direct key simulation. Streaming: inserts text in real-time as you speak.")

        self._restore_clip_var = ctk.BooleanVar(value=self.settings.restore_clipboard)
        ctk.CTkCheckBox(
            card, text="Restore clipboard after paste",
            variable=self._restore_clip_var,
            font=ctk.CTkFont(size=13),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(anchor="w", padx=14, pady=(8, 2))
        self._desc(card, "Restores your previous clipboard content after pasting the transcription.")

        self._trailing_space_var = ctk.BooleanVar(value=self.settings.add_trailing_space)
        ctk.CTkCheckBox(
            card, text="Add trailing space",
            variable=self._trailing_space_var,
            font=ctk.CTkFont(size=13),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(anchor="w", padx=14, pady=(8, 2))
        self._desc(card, "Adds a space after the transcription so you can keep typing naturally.")

        ctk.CTkFrame(card, height=6, fg_color="transparent").pack()

        # ── LLM Normalization ────────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "LLM Normalization")

        self._desc(card, "AI model used to fix grammar, punctuation, and formatting of transcribed text.")

        self._llm_provider_var = ctk.StringVar(value=self.settings.normalize_llm_provider)
        ctk.CTkSegmentedButton(
            card, values=["openai", "gemini"],
            variable=self._llm_provider_var,
            command=lambda _: self._on_llm_provider_change(),
            font=ctk.CTkFont(size=13),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
        ).pack(fill="x", padx=14, pady=(6, 8))

        # OpenAI LLM frame
        self._llm_openai_frame = ctk.CTkFrame(card, fg_color="transparent")

        row = self._row(self._llm_openai_frame)
        ctk.CTkLabel(row, text="API Key", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")
        self._llm_openai_key_var = ctk.StringVar(value=self.settings.openai_api_key)
        ctk.CTkEntry(
            row, textvariable=self._llm_openai_key_var, show="*",
            fg_color=CARD_BG, border_color=BORDER, width=200,
        ).pack(side="right")
        self._desc(self._llm_openai_frame, "Your OpenAI API key. Shared with Cloud STT if both are used.", padx=14)

        row = self._row(self._llm_openai_frame, pady=(3, 6))
        ctk.CTkLabel(row, text="Model", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")
        self._llm_model_var = ctk.StringVar(value=self.settings.normalize_llm_model)
        ctk.CTkOptionMenu(
            row, variable=self._llm_model_var,
            values=["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1-nano"],
            fg_color=CARD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")
        self._desc(self._llm_openai_frame, "gpt-4o-mini is fast and cheap. gpt-4o gives best quality.", padx=14)

        # Gemini LLM frame
        self._llm_gemini_frame = ctk.CTkFrame(card, fg_color="transparent")

        row = self._row(self._llm_gemini_frame)
        ctk.CTkLabel(row, text="API Key", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")
        self._gemini_key_var = ctk.StringVar(value=self.settings.gemini_api_key)
        ctk.CTkEntry(
            row, textvariable=self._gemini_key_var, show="*",
            fg_color=CARD_BG, border_color=BORDER, width=200,
        ).pack(side="right")
        self._desc(self._llm_gemini_frame, "Your Google Gemini API key from Google AI Studio.", padx=14)

        ctk.CTkFrame(self._llm_gemini_frame, height=6, fg_color="transparent").pack()

        self._on_llm_provider_change()

    def _build_app_tab(self, tab):
        scroll = self._tab_scroll(tab)

        # ── Startup ──────────────────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Startup")

        self._autostart_var = ctk.BooleanVar(value=self.settings.auto_start_with_windows)
        ctk.CTkCheckBox(
            card, text="Start with Windows",
            variable=self._autostart_var,
            font=ctk.CTkFont(size=13),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(anchor="w", padx=14, pady=(0, 2))
        self._desc(card, "Automatically launch WhisperTyping when you log into Windows.")

        ctk.CTkFrame(card, height=8, fg_color="transparent").pack()

        # ── Interface ────────────────────────────
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Interface")

        self._floating_var = ctk.BooleanVar(value=self.settings.show_floating_window)
        ctk.CTkCheckBox(
            card, text="Show floating status window",
            variable=self._floating_var,
            font=ctk.CTkFont(size=13),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(anchor="w", padx=14, pady=(0, 2))
        self._desc(card, "Small overlay that shows recording/processing status on screen.")

        self._always_on_top_var = ctk.BooleanVar(value=self.settings.always_on_top)
        ctk.CTkCheckBox(
            card, text="Always on top",
            variable=self._always_on_top_var,
            font=ctk.CTkFont(size=13),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(anchor="w", padx=14, pady=(10, 2))
        self._desc(card, "Keep the floating window above all other windows.")

        ctk.CTkFrame(card, height=8, fg_color="transparent").pack()

    # ── UI Helpers ────────────────────────────────────────────────────────────

    def _tab_scroll(self, tab) -> ctk.CTkScrollableFrame:
        """Create a scrollable frame that fills a tab."""
        scroll = ctk.CTkScrollableFrame(
            tab, fg_color=CARD_BG,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=ACCENT,
        )
        scroll.pack(fill="both", expand=True)
        return scroll

    def _row(self, parent, pady=(3, 3)) -> ctk.CTkFrame:
        """Create a horizontal row frame."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=pady)
        return row

    def _section_label(self, parent, text: str):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=TEXT_BRIGHT,
        ).pack(anchor="w", padx=14, pady=(10, 6))

    def _desc(self, parent, text: str, padx: int = 14):
        """Add a small description label."""
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=11),
            text_color=TEXT_DIM,
            anchor="w",
            justify="left",
            wraplength=440,
        ).pack(anchor="w", padx=padx, pady=(0, 6))

    def _make_hotkey_recorder(self, parent, hotkey_var: ctk.StringVar, start_fn):
        """Create a hotkey row (label + display + record button). Returns (display_label, button)."""
        row = self._row(parent, pady=(3, 3))
        ctk.CTkLabel(row, text="Hotkey", text_color=TEXT_DIM, width=60, anchor="w").pack(side="left")

        display = ctk.CTkLabel(
            row, text=hotkey_var.get(),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT, anchor="w",
        )
        display.pack(side="left", padx=(4, 10))

        btn = ctk.CTkButton(
            row, text="Record", width=80, height=28,
            font=ctk.CTkFont(size=12),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=start_fn,
        )
        btn.pack(side="right")
        return display, btn

    # ── Provider / trigger visibility ─────────────────────────────────────────

    def _on_provider_change(self):
        if self._provider_var.get() == "local":
            self._cloud_frame.pack_forget()
            self._local_frame.pack(fill="x", after=self._local_frame.master.winfo_children()[2])
        else:
            self._local_frame.pack_forget()
            self._cloud_frame.pack(fill="x", after=self._cloud_frame.master.winfo_children()[2])

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

    # ── Hotkey recording ──────────────────────────────────────────────────────

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

    # ── Save / Cancel ─────────────────────────────────────────────────────────

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

        # Sync OpenAI API key — LLM field takes priority, fall back to Cloud STT field
        llm_key = self._llm_openai_key_var.get()
        cloud_key = self._api_key_var.get()
        if llm_key:
            self.settings.openai_api_key = llm_key
        elif cloud_key:
            self.settings.openai_api_key = cloud_key

        # Application
        self.settings.auto_start_with_windows = self._autostart_var.get()
        self.settings.show_floating_window = self._floating_var.get()
        self.settings.always_on_top = self._always_on_top_var.get()

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
