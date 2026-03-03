import customtkinter as ctk
import logging
from datetime import datetime
from typing import Optional

from core.history import TranscriptionHistory, HistoryEntry

logger = logging.getLogger(__name__)

# Colors (matching settings_window)
CARD_BG = "#1e1e2e"
SECTION_BG = "#272740"
ENTRY_BG = "#2a2a44"
ACCENT = "#6c5ce7"
ACCENT_HOVER = "#5a4bd1"
DANGER = "#e74c3c"
DANGER_HOVER = "#c0392b"
SUCCESS = "#2ecc71"
TEXT_DIM = "#888899"
TEXT_BRIGHT = "#e0e0e0"
BORDER = "#3a3a5c"


class HistoryWindow:
    """Modern window showing transcription history."""

    def __init__(
        self,
        parent: ctk.CTk,
        history: TranscriptionHistory,
    ):
        self._parent = parent
        self._history = history
        self._window: Optional[ctk.CTkToplevel] = None
        self._known_count = 0
        self._poll_id = None

    def show(self):
        if self._window is not None and self._window.winfo_exists():
            self._window.focus()
            return

        self._window = ctk.CTkToplevel(self._parent)
        self._window.title("WhisperTyping — History")
        self._window.geometry("540x540")
        self._window.resizable(True, True)
        self._window.configure(fg_color=CARD_BG)
        self._window.protocol("WM_DELETE_WINDOW", self._on_close)

        # Header
        header = ctk.CTkFrame(self._window, fg_color=CARD_BG)
        header.pack(fill="x", padx=20, pady=(16, 8))

        ctk.CTkLabel(
            header, text="History",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=TEXT_BRIGHT,
        ).pack(side="left")

        self._count_label = ctk.CTkLabel(
            header, text="",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_DIM,
        )
        self._count_label.pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            header, text="Clear All", width=80, height=30,
            font=ctk.CTkFont(size=12),
            fg_color=DANGER, hover_color=DANGER_HOVER,
            corner_radius=8,
            command=self._clear_history,
        ).pack(side="right")

        # Scrollable list
        self._scroll = ctk.CTkScrollableFrame(
            self._window,
            fg_color=CARD_BG,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=ACCENT,
        )
        self._scroll.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self._populate()
        self._start_polling()

    def _populate(self):
        for widget in self._scroll.winfo_children():
            widget.destroy()

        entries = self._history.get_all()
        self._known_count = len(entries)
        self._count_label.configure(text=f"({self._known_count})" if self._known_count else "")

        if not entries:
            empty_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
            empty_frame.pack(fill="both", expand=True, pady=60)
            ctk.CTkLabel(
                empty_frame, text="No transcriptions yet",
                font=ctk.CTkFont(size=15),
                text_color=TEXT_DIM,
            ).pack()
            ctk.CTkLabel(
                empty_frame, text="Press your hotkey and speak",
                font=ctk.CTkFont(size=12),
                text_color=TEXT_DIM,
            ).pack(pady=(4, 0))
            return

        for entry in entries:
            self._add_entry_widget(entry)

    def _add_entry_widget(self, entry: HistoryEntry):
        card = ctk.CTkFrame(
            self._scroll,
            corner_radius=10,
            fg_color=ENTRY_BG,
            border_width=1,
            border_color=BORDER,
        )
        card.pack(fill="x", pady=4, padx=4)

        # Header row: timestamp + language badge
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8, 2))

        try:
            dt = datetime.fromisoformat(entry.timestamp)
            time_str = dt.strftime("%d.%m.%Y  %H:%M:%S")
        except (ValueError, TypeError):
            time_str = entry.timestamp

        ctk.CTkLabel(
            header, text=time_str,
            font=ctk.CTkFont(size=11),
            text_color=TEXT_DIM,
        ).pack(side="left")

        # Language badge
        lang = entry.language.upper() if entry.language else "?"
        badge = ctk.CTkLabel(
            header, text=f" {lang} ",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=ACCENT,
            corner_radius=4,
            text_color="white",
        )
        badge.pack(side="right", padx=(4, 0))

        # Processing time
        if entry.processing_time_seconds and entry.processing_time_seconds > 0:
            ctk.CTkLabel(
                header,
                text=f"{entry.processing_time_seconds:.1f}s",
                font=ctk.CTkFont(size=10),
                text_color=TEXT_DIM,
            ).pack(side="right", padx=(0, 6))

        # Duration
        if entry.duration_seconds and entry.duration_seconds > 0:
            dur = entry.duration_seconds
            dur_text = f"{dur:.0f}s" if dur < 60 else f"{dur / 60:.1f}m"
            ctk.CTkLabel(
                header,
                text=f"{dur_text}",
                font=ctk.CTkFont(size=10),
                text_color=TEXT_DIM,
            ).pack(side="right", padx=(0, 6))

        # Text content
        ctk.CTkLabel(
            card, text=entry.text,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_BRIGHT,
            anchor="w", justify="left",
            wraplength=470,
        ).pack(fill="x", padx=12, pady=(2, 4))

        # Copy button row
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 8))

        copy_btn = ctk.CTkButton(
            btn_row, text="Copy", width=56, height=24,
            font=ctk.CTkFont(size=11),
            fg_color=SECTION_BG, hover_color=ACCENT,
            border_width=1, border_color=BORDER,
            corner_radius=6,
            command=lambda t=entry.text, b=None: self._copy_text(t, copy_btn),
        )
        copy_btn.pack(side="right")

    def _copy_text(self, text: str, btn: ctk.CTkButton):
        if self._window:
            self._window.clipboard_clear()
            self._window.clipboard_append(text)
            # Flash feedback
            btn.configure(text="Copied!", fg_color=SUCCESS)
            self._window.after(
                1200,
                lambda: btn.configure(text="Copy", fg_color=SECTION_BG)
                if btn.winfo_exists() else None,
            )

    def _clear_history(self):
        self._history.clear()
        self._populate()

    def _start_polling(self):
        self._known_count = len(self._history)
        self._poll()

    def _poll(self):
        if not self._window or not self._window.winfo_exists():
            return
        current = len(self._history)
        if current != self._known_count:
            self._populate()
        self._poll_id = self._window.after(1000, self._poll)

    def _on_close(self):
        if self._poll_id and self._window:
            self._window.after_cancel(self._poll_id)
        if self._window:
            self._window.destroy()
            self._window = None
