import tkinter as tk
import customtkinter as ctk
import keyboard
import logging
from typing import Optional, Callable

from config.resources import ICON_PATH
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

# ── Color tokens ──────────────────────────────────────────────────────────────
CARD_BG      = "#13131f"   # main window background
SECTION_BG   = "#1d1d30"   # card background
INPUT_BG     = "#0f0f1c"   # entry / option-menu background
ACCENT       = "#7c6af0"   # primary violet
ACCENT_HOVER = "#6a58dc"
DANGER       = "#e74c3c"
DANGER_HOVER = "#c0392b"
TEXT_DIM     = "#8080a0"
TEXT_BRIGHT  = "#e0e0f0"
BORDER       = "#2a2a46"
TIP_BG       = "#1d1d30"   # tooltip popup background


class _Tooltip:
    """Hover tooltip for any CTK/tkinter widget. Appears after 700 ms."""

    def __init__(self, widget, text: str):
        self._w    = widget
        self._text = text
        self._win  = None
        self._job  = None
        try:
            widget.bind("<Enter>",       self._schedule, add="+")
            widget.bind("<Leave>",       self._cancel,   add="+")
            widget.bind("<ButtonPress>", self._cancel,   add="+")
        except (NotImplementedError, AttributeError):
            # CTkSegmentedButton and some composite widgets don't support bind.
            # Fall back to the underlying tkinter widget if available.
            inner = getattr(widget, "_canvas", None) or getattr(widget, "_label", None)
            if inner:
                inner.bind("<Enter>",       self._schedule, add="+")
                inner.bind("<Leave>",       self._cancel,   add="+")
                inner.bind("<ButtonPress>", self._cancel,   add="+")

    def _schedule(self, _=None):
        self._job = self._w.after(700, self._show)

    def _cancel(self, _=None):
        if self._job:
            self._w.after_cancel(self._job)
            self._job = None
        if self._win:
            self._win.destroy()
            self._win = None

    def _show(self):
        self._job = None
        if self._win:
            return
        x = self._w.winfo_rootx()
        y = self._w.winfo_rooty() + self._w.winfo_height() + 6
        tw = tk.Toplevel(self._w)
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-topmost", True)
        tw.configure(bg=BORDER)
        frame = tk.Frame(tw, bg=TIP_BG, padx=10, pady=8)
        frame.pack(padx=1, pady=1)
        tk.Label(
            frame,
            text=self._text,
            bg=TIP_BG, fg=TEXT_BRIGHT,
            font=("Segoe UI", 10),
            wraplength=300,
            justify="left",
        ).pack()
        tw.update_idletasks()
        # Keep tooltip on screen horizontally
        sw   = tw.winfo_screenwidth()
        tw_w = tw.winfo_reqwidth()
        if x + tw_w > sw - 12:
            x = sw - tw_w - 12
        tw.wm_geometry(f"+{x}+{y}")
        self._win = tw


def _make_card(parent, **kwargs):
    return ctk.CTkFrame(parent, corner_radius=12, fg_color=SECTION_BG,
                        border_width=1, border_color=BORDER, **kwargs)


class SettingsWindow:
    """Tabbed settings dialog with hover tooltips."""

    def __init__(self, parent: ctk.CTk, settings: AppSettings,
                 on_save: Optional[Callable[[AppSettings], None]] = None):
        self.settings  = settings
        self.on_save   = on_save
        self._window: Optional[ctk.CTkToplevel] = None
        self._parent   = parent
        self._hotkey_recording      = False
        self._norm_hotkey_recording = False

    def show(self):
        if self._window is not None and self._window.winfo_exists():
            self._window.focus()
            return

        self._window = ctk.CTkToplevel(self._parent)
        self._window.title("WhisperTyping — Settings")
        self._window.geometry("530x540")
        self._window.resizable(False, True)
        self._window.configure(fg_color=CARD_BG)
        self._window.grab_set()
        import os
        if os.path.exists(ICON_PATH):
            self._window.after(100, lambda: self._window.iconbitmap(ICON_PATH))

        # ── Header ────────────────────────────────
        header = ctk.CTkFrame(self._window, fg_color=CARD_BG)
        header.pack(fill="x", padx=24, pady=(20, 0))
        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(fill="x")
        ctk.CTkLabel(
            title_row, text="Settings",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=TEXT_BRIGHT,
        ).pack(side="left")
        ctk.CTkLabel(
            title_row, text="WhisperTyping",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT_DIM,
        ).pack(side="left", padx=(12, 0), pady=(6, 0))
        ctk.CTkFrame(self._window, height=1, fg_color=BORDER).pack(fill="x", padx=14, pady=(12, 2))

        # ── Tab view ──────────────────────────────
        tabview = ctk.CTkTabview(
            self._window,
            fg_color=CARD_BG,
            segmented_button_fg_color=SECTION_BG,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_color=SECTION_BG,
            segmented_button_unselected_hover_color="#252548",
            border_width=0,
        )
        tabview.pack(fill="both", expand=True, padx=14)
        for name in ("Recognition", "Hotkeys", "Output", "App"):
            tabview.add(name)

        self._build_recognition_tab(tabview.tab("Recognition"))
        self._build_hotkeys_tab(tabview.tab("Hotkeys"))
        self._build_output_tab(tabview.tab("Output"))
        self._build_app_tab(tabview.tab("App"))

        # ── Buttons ───────────────────────────────
        ctk.CTkFrame(self._window, height=1, fg_color=BORDER).pack(fill="x", padx=14)
        btn_frame = ctk.CTkFrame(self._window, fg_color=CARD_BG)
        btn_frame.pack(fill="x", padx=20, pady=(10, 16))
        ctk.CTkButton(
            btn_frame, text="Save", command=self._save,
            width=110, height=36,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER, corner_radius=10,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            btn_frame, text="Cancel", command=self._cancel,
            width=110, height=36, font=ctk.CTkFont(size=14),
            fg_color="transparent", hover_color=SECTION_BG,
            border_width=1, border_color=BORDER, corner_radius=10,
        ).pack(side="right")

    # ── Tab builders ──────────────────────────────────────────────────────────

    def _build_recognition_tab(self, tab):
        scroll = self._tab_scroll(tab)

        # STT Provider card
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Speech Recognition")

        self._provider_var = ctk.StringVar(value=self.settings.stt_provider)
        seg = ctk.CTkSegmentedButton(
            card, values=["local", "cloud"],
            variable=self._provider_var,
            command=lambda _: self._on_provider_change(),
            font=ctk.CTkFont(size=13),
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
        )
        seg.pack(fill="x", padx=14, pady=(0, 12))
        _Tooltip(seg,
            "Local — private, free, runs on your PC (GPU recommended).\n"
            "Cloud — sends audio to OpenAI, works on any PC but costs money per minute.")

        # Local sub-frame
        self._local_frame = ctk.CTkFrame(card, fg_color="transparent")

        row = self._row(self._local_frame)
        lbl = self._lbl(row, "Model")
        _Tooltip(lbl,
            "tiny/base: fast but unreliable — may output wrong language.\n"
            "small: decent balance.\n"
            "large-v3: best accuracy, needs ~6 GB VRAM (GPU) or ~8 GB RAM (CPU).\n"
            "Recommended: large-v3 on CUDA.")
        self._model_size_var = ctk.StringVar(value=self.settings.local_model_size)
        ctk.CTkOptionMenu(
            row, variable=self._model_size_var, values=LOCAL_MODEL_SIZES,
            fg_color=INPUT_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200,
        ).pack(side="right")

        row = self._row(self._local_frame)
        lbl = self._lbl(row, "Device")
        _Tooltip(lbl,
            "cuda (NVIDIA GPU): ~0.5s per phrase — fastest.\n"
            "cpu: works on any PC — tiny/small are ok, large-v3 on CPU takes 10–30s.\n"
            "Switching device reloads the model automatically.")
        self._device_var = ctk.StringVar(value=self.settings.device)
        ctk.CTkOptionMenu(
            row, variable=self._device_var, values=["cuda", "cpu"],
            fg_color=INPUT_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            width=200, command=lambda _: self._on_device_change(),
        ).pack(side="right")

        row = self._row(self._local_frame, pady=(3, 10))
        lbl = self._lbl(row, "Precision")
        _Tooltip(lbl,
            "float16: GPU only, best speed and accuracy.\n"
            "int8: CPU/GPU, lower memory, slightly less accurate.\n"
            "int8_float16: mixed mode for GPU.\n"
            "Auto-adjusts when you switch device.")
        self._compute_var = ctk.StringVar(value=self.settings.compute_type)
        self._compute_menu = ctk.CTkOptionMenu(
            row, variable=self._compute_var, values=[ct.value for ct in ComputeType],
            fg_color=INPUT_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER, width=200)
        self._compute_menu.pack(side="right")

        # Cloud sub-frame
        self._cloud_frame = ctk.CTkFrame(card, fg_color="transparent")

        row = self._row(self._cloud_frame)
        lbl = self._lbl(row, "API Key")
        _Tooltip(lbl, "Your OpenAI API key (sk-…). Required for cloud transcription.")
        self._api_key_var = ctk.StringVar(value=self.settings.openai_api_key)
        ctk.CTkEntry(row, textvariable=self._api_key_var, show="*",
                     fg_color=INPUT_BG, border_color=BORDER, width=200).pack(side="right")

        row = self._row(self._cloud_frame, pady=(3, 10))
        lbl = self._lbl(row, "Model")
        _Tooltip(lbl, "Cloud STT model. Currently only whisper-1 is available.")
        self._cloud_model_var = ctk.StringVar(value=self.settings.openai_model)
        ctk.CTkOptionMenu(
            row, variable=self._cloud_model_var, values=["whisper-1"],
            fg_color=INPUT_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER, width=200,
        ).pack(side="right")

        self._on_provider_change()

        # Language card
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Language",
            tip="⚠ With tiny/base models, always set language explicitly —\n"
                "auto-detect is unreliable and may output the wrong language.\n"
                "With large-v3, auto works well.")

        lang_row = ctk.CTkFrame(card, fg_color="transparent")
        lang_row.pack(fill="x", padx=14, pady=(0, 12))
        self._lang_var = ctk.StringVar(value=self.settings.language)
        for code, display in SUPPORTED_LANGUAGES.items():
            ctk.CTkRadioButton(
                lang_row, text=display, variable=self._lang_var, value=code,
                font=ctk.CTkFont(size=13), fg_color=ACCENT, hover_color=ACCENT_HOVER,
            ).pack(side="left", padx=(0, 14))

        # Microphone card
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Microphone",
            tip="Audio input device used for recording.\nSystem Default works for most setups.")

        devices       = AudioRecorder.list_devices()
        device_names  = ["System Default"] + [d["name"] for d in devices]
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
            fg_color=INPUT_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
        ).pack(fill="x", padx=14, pady=(0, 12))

    def _build_hotkeys_tab(self, tab):
        scroll = self._tab_scroll(tab)

        # Main Trigger card
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Main Trigger",
            tip="Keyboard combo or mouse button that starts/stops recording.")

        self._trigger_type_var = ctk.StringVar(value=self.settings.trigger_type)
        ctk.CTkSegmentedButton(
            card, values=[TRIGGER_TYPE_KEYBOARD, TRIGGER_TYPE_MOUSE],
            variable=self._trigger_type_var,
            command=lambda _: self._on_trigger_type_change(),
            font=ctk.CTkFont(size=13),
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
        ).pack(fill="x", padx=14, pady=(0, 8))

        self._kb_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._hotkey_var = ctk.StringVar(value=self.settings.trigger_key)
        self._hotkey_display, self._hotkey_btn = self._make_hotkey_recorder(
            self._kb_frame, self._hotkey_var, start_fn=self._start_hotkey_recording)

        self._mouse_frame = ctk.CTkFrame(card, fg_color="transparent")
        row = self._row(self._mouse_frame, pady=(3, 8))
        self._lbl(row, "Button", width=60)
        self._mouse_btn_var = ctk.StringVar(value=self.settings.trigger_mouse_button)
        ctk.CTkOptionMenu(
            row, variable=self._mouse_btn_var, values=list(MOUSE_BUTTONS.keys()),
            fg_color=INPUT_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER, width=200,
        ).pack(side="right")

        self._on_trigger_type_change()

        row = self._row(card, pady=(4, 12))
        lbl = self._lbl(row, "Mode", width=60)
        _Tooltip(lbl,
            "Push-to-talk: hold key while speaking, release to transcribe.\n"
            "Toggle: press once to start recording, press again to stop.")
        self._mode_var = ctk.StringVar(value=self.settings.trigger_mode)
        ctk.CTkSegmentedButton(
            row, values=["push_to_talk", "toggle"],
            variable=self._mode_var,
            font=ctk.CTkFont(size=12),
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
        ).pack(side="right")

        # Normalize Trigger card
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Normalize Trigger",
            tip="Second hotkey that transcribes AND runs AI text cleanup in one step.")

        self._norm_enabled_var = ctk.BooleanVar(value=self.settings.normalize_trigger_enabled)
        cb = ctk.CTkCheckBox(card, text="Enable normalize trigger",
                             variable=self._norm_enabled_var,
                             font=ctk.CTkFont(size=13), fg_color=ACCENT, hover_color=ACCENT_HOVER)
        cb.pack(anchor="w", padx=14, pady=(0, 8))

        self._norm_trigger_type_var = ctk.StringVar(value=self.settings.normalize_trigger_type)
        ctk.CTkSegmentedButton(
            card, values=[TRIGGER_TYPE_KEYBOARD, TRIGGER_TYPE_MOUSE],
            variable=self._norm_trigger_type_var,
            command=lambda _: self._on_norm_trigger_type_change(),
            font=ctk.CTkFont(size=12),
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
        ).pack(fill="x", padx=14, pady=(0, 8))

        self._norm_kb_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._norm_hotkey_var = ctk.StringVar(value=self.settings.normalize_trigger_key)
        self._norm_hotkey_display, self._norm_hotkey_btn = self._make_hotkey_recorder(
            self._norm_kb_frame, self._norm_hotkey_var, start_fn=self._start_norm_hotkey_recording)

        self._norm_mouse_frame = ctk.CTkFrame(card, fg_color="transparent")
        row = self._row(self._norm_mouse_frame, pady=(3, 8))
        self._lbl(row, "Button", width=60)
        self._norm_mouse_btn_var = ctk.StringVar(value=self.settings.normalize_trigger_mouse_button)
        ctk.CTkOptionMenu(
            row, variable=self._norm_mouse_btn_var, values=list(MOUSE_BUTTONS.keys()),
            fg_color=INPUT_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER, width=200,
        ).pack(side="right")

        self._on_norm_trigger_type_change()

        row = self._row(card, pady=(4, 12))
        lbl = self._lbl(row, "Mode", width=60)
        _Tooltip(lbl, "Push-to-talk: hold key while speaking. Toggle: press once to start, again to stop.")
        self._norm_mode_var = ctk.StringVar(value=self.settings.normalize_trigger_mode)
        ctk.CTkSegmentedButton(
            row, values=["push_to_talk", "toggle"],
            variable=self._norm_mode_var,
            font=ctk.CTkFont(size=12),
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
        ).pack(side="right")

    def _build_output_tab(self, tab):
        scroll = self._tab_scroll(tab)

        # Text Injection card
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Text Injection")

        row = self._row(card)
        lbl = self._lbl(row, "Method", width=90)
        _Tooltip(lbl,
            "Clipboard: most compatible, pastes full text after speaking.\n"
            "SendInput: simulates keyboard — works where clipboard is blocked.\n"
            "Streaming: types in real-time while you speak — needs fast GPU\n"
            "or small model on CPU, otherwise may lag or overflow.")
        self._injection_var = ctk.StringVar(value=self.settings.injection_method)
        ctk.CTkOptionMenu(
            row, variable=self._injection_var,
            values=["clipboard", "sendinput", "streaming"],
            fg_color=INPUT_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER, width=200,
        ).pack(side="right")

        self._restore_clip_var = ctk.BooleanVar(value=self.settings.restore_clipboard)
        cb = ctk.CTkCheckBox(card, text="Restore clipboard after paste",
                             variable=self._restore_clip_var,
                             font=ctk.CTkFont(size=13), fg_color=ACCENT, hover_color=ACCENT_HOVER)
        cb.pack(anchor="w", padx=14, pady=(8, 4))
        _Tooltip(cb, "Restores your previous clipboard content after pasting the transcription.")

        self._trailing_space_var = ctk.BooleanVar(value=self.settings.add_trailing_space)
        cb = ctk.CTkCheckBox(card, text="Add trailing space",
                             variable=self._trailing_space_var,
                             font=ctk.CTkFont(size=13), fg_color=ACCENT, hover_color=ACCENT_HOVER)
        cb.pack(anchor="w", padx=14, pady=(4, 12))
        _Tooltip(cb, "Adds a space after the transcription so you can keep typing naturally.")

        # LLM Normalization card
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "LLM Normalization",
            tip="AI model that fixes grammar, punctuation, and formatting of transcribed text.")

        self._llm_provider_var = ctk.StringVar(value=self.settings.normalize_llm_provider)
        ctk.CTkSegmentedButton(
            card, values=["openai", "gemini"],
            variable=self._llm_provider_var,
            command=lambda _: self._on_llm_provider_change(),
            font=ctk.CTkFont(size=13),
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
        ).pack(fill="x", padx=14, pady=(0, 8))

        # OpenAI LLM frame
        self._llm_openai_frame = ctk.CTkFrame(card, fg_color="transparent")

        row = self._row(self._llm_openai_frame)
        lbl = self._lbl(row, "API Key", width=60)
        _Tooltip(lbl, "Your OpenAI API key. Shared with Cloud STT if both are used.")
        self._llm_openai_key_var = ctk.StringVar(value=self.settings.openai_api_key)
        ctk.CTkEntry(row, textvariable=self._llm_openai_key_var, show="*",
                     fg_color=INPUT_BG, border_color=BORDER, width=200).pack(side="right")

        row = self._row(self._llm_openai_frame, pady=(3, 10))
        lbl = self._lbl(row, "Model", width=60)
        _Tooltip(lbl, "gpt-4o-mini: fast and cheap — recommended.\ngpt-4o: best quality, higher cost.")
        self._llm_model_var = ctk.StringVar(value=self.settings.normalize_llm_model)
        ctk.CTkOptionMenu(
            row, variable=self._llm_model_var,
            values=["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1-nano"],
            fg_color=INPUT_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER, width=200,
        ).pack(side="right")

        # Gemini LLM frame
        self._llm_gemini_frame = ctk.CTkFrame(card, fg_color="transparent")

        row = self._row(self._llm_gemini_frame)
        lbl = self._lbl(row, "API Key", width=60)
        _Tooltip(lbl, "Your Google Gemini API key from Google AI Studio (aistudio.google.com).")
        self._gemini_key_var = ctk.StringVar(value=self.settings.gemini_api_key)
        ctk.CTkEntry(row, textvariable=self._gemini_key_var, show="*",
                     fg_color=INPUT_BG, border_color=BORDER, width=200).pack(side="right")

        ctk.CTkFrame(self._llm_gemini_frame, height=10, fg_color="transparent").pack()

        self._on_llm_provider_change()

    def _build_app_tab(self, tab):
        scroll = self._tab_scroll(tab)

        # Startup card
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Startup")

        self._autostart_var = ctk.BooleanVar(value=self.settings.auto_start_with_windows)
        cb = ctk.CTkCheckBox(card, text="Start with Windows",
                             variable=self._autostart_var,
                             font=ctk.CTkFont(size=13), fg_color=ACCENT, hover_color=ACCENT_HOVER)
        cb.pack(anchor="w", padx=14, pady=(0, 12))
        _Tooltip(cb, "Automatically launch WhisperTyping when you log into Windows.")

        # Interface card
        card = _make_card(scroll)
        card.pack(fill="x", pady=6, padx=4)
        self._section_label(card, "Interface")

        self._floating_var = ctk.BooleanVar(value=self.settings.show_floating_window)
        cb = ctk.CTkCheckBox(card, text="Show floating status window",
                             variable=self._floating_var,
                             font=ctk.CTkFont(size=13), fg_color=ACCENT, hover_color=ACCENT_HOVER)
        cb.pack(anchor="w", padx=14, pady=(0, 8))
        _Tooltip(cb, "Small overlay that shows recording/processing status on screen.")

        self._always_on_top_var = ctk.BooleanVar(value=self.settings.always_on_top)
        cb = ctk.CTkCheckBox(card, text="Always on top",
                             variable=self._always_on_top_var,
                             font=ctk.CTkFont(size=13), fg_color=ACCENT, hover_color=ACCENT_HOVER)
        cb.pack(anchor="w", padx=14, pady=(0, 12))
        _Tooltip(cb, "Keep the floating status window above all other windows.")

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _tab_scroll(self, tab):
        """Wrap tab in a scrollable frame so long tabs can scroll."""
        tab.configure(fg_color=CARD_BG)
        scroll = ctk.CTkScrollableFrame(
            tab, fg_color=CARD_BG,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=ACCENT,
        )
        scroll.pack(fill="both", expand=True)
        return scroll

    def _row(self, parent, pady=(3, 3)) -> ctk.CTkFrame:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=pady)
        return row

    def _lbl(self, parent, text: str, width: int = 90) -> ctk.CTkLabel:
        """Create and pack a dim setting label. Returns widget for tooltip attachment."""
        lbl = ctk.CTkLabel(parent, text=text, text_color=TEXT_DIM, width=width, anchor="w")
        lbl.pack(side="left")
        return lbl

    def _section_label(self, parent, text: str, tip: str = ""):
        """Section heading. ⓘ with hover tooltip when tip is given."""
        display = f"{text}  ⓘ" if tip else text
        lbl = ctk.CTkLabel(
            parent, text=display,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=TEXT_BRIGHT,
        )
        lbl.pack(anchor="w", padx=14, pady=(10, 6))
        if tip:
            _Tooltip(lbl, tip)

    def _make_hotkey_recorder(self, parent, hotkey_var: ctk.StringVar, start_fn):
        row = self._row(parent, pady=(3, 3))
        self._lbl(row, "Hotkey", width=60)
        display = ctk.CTkLabel(
            row, text=hotkey_var.get(),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT, anchor="w",
        )
        display.pack(side="left", padx=(4, 10))
        btn = ctk.CTkButton(
            row, text="Record", width=80, height=28, font=ctk.CTkFont(size=12),
            fg_color=ACCENT, hover_color=ACCENT_HOVER, command=start_fn,
        )
        btn.pack(side="right")
        return display, btn

    # ── Visibility toggles ────────────────────────────────────────────────────

    def _on_device_change(self):
        device  = self._device_var.get()
        current = self._compute_var.get()
        if device == "cpu"  and current == "float16":
            self._compute_var.set("int8")
        elif device == "cuda" and current == "int8":
            self._compute_var.set("float16")

    def _on_provider_change(self):
        if self._provider_var.get() == "local":
            self._cloud_frame.pack_forget()
            self._local_frame.pack(fill="x")
        else:
            self._local_frame.pack_forget()
            self._cloud_frame.pack(fill="x")

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
            def _update():
                self._hotkey_display.configure(text=combo, text_color=ACCENT)
                self._hotkey_btn.configure(text="Record", fg_color=ACCENT)
            if self._window and self._window.winfo_exists():
                self._window.after(0, _update)

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
            def _update():
                self._norm_hotkey_display.configure(text=combo, text_color=ACCENT)
                self._norm_hotkey_btn.configure(text="Record", fg_color=ACCENT)
            if self._window and self._window.winfo_exists():
                self._window.after(0, _update)

        hook = keyboard.hook(_on_key)

    # ── Save / Cancel ─────────────────────────────────────────────────────────

    def _save(self):
        self.settings.stt_provider        = self._provider_var.get()
        self.settings.local_model_size    = self._model_size_var.get()
        self.settings.device              = self._device_var.get()
        self.settings.compute_type        = self._compute_var.get()
        self.settings.openai_api_key      = self._api_key_var.get()
        self.settings.openai_model        = self._cloud_model_var.get()
        self.settings.language            = self._lang_var.get()
        self.settings.microphone_device_index = self._device_map.get(self._mic_var.get(), -1)

        self.settings.trigger_type         = self._trigger_type_var.get()
        self.settings.trigger_key          = self._hotkey_var.get()
        self.settings.trigger_mouse_button = self._mouse_btn_var.get()
        self.settings.trigger_mode         = self._mode_var.get()

        self.settings.injection_method    = self._injection_var.get()
        self.settings.restore_clipboard   = self._restore_clip_var.get()
        self.settings.add_trailing_space  = self._trailing_space_var.get()

        self.settings.normalize_trigger_enabled      = self._norm_enabled_var.get()
        self.settings.normalize_trigger_type         = self._norm_trigger_type_var.get()
        self.settings.normalize_trigger_key          = self._norm_hotkey_var.get()
        self.settings.normalize_trigger_mouse_button = self._norm_mouse_btn_var.get()
        self.settings.normalize_trigger_mode         = self._norm_mode_var.get()
        self.settings.normalize_llm_provider         = self._llm_provider_var.get()
        self.settings.normalize_llm_model            = self._llm_model_var.get()
        self.settings.gemini_api_key                 = self._gemini_key_var.get()

        # Sync OpenAI key — LLM field takes priority
        llm_key   = self._llm_openai_key_var.get()
        cloud_key = self._api_key_var.get()
        if llm_key:
            self.settings.openai_api_key = llm_key
        elif cloud_key:
            self.settings.openai_api_key = cloud_key

        self.settings.auto_start_with_windows = self._autostart_var.get()
        self.settings.show_floating_window    = self._floating_var.get()
        self.settings.always_on_top           = self._always_on_top_var.get()

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
            self._hotkey_recording      = False
            self._norm_hotkey_recording = False
        if self._window:
            self._window.destroy()
            self._window = None
