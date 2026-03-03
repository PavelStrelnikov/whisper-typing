import pystray
from PIL import Image, ImageDraw
import threading
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class TrayIcon:
    """System tray icon with context menu."""

    def __init__(
        self,
        on_show_window: Optional[Callable] = None,
        on_settings: Optional[Callable] = None,
        on_history: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
    ):
        self.on_show_window = on_show_window
        self.on_settings = on_settings
        self.on_history = on_history
        self.on_quit = on_quit
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        icon_image = self._create_icon("#4287f5")

        menu = pystray.Menu(
            pystray.MenuItem("Show Window", self._on_show, default=True),
            pystray.MenuItem("History", self._on_history),
            pystray.MenuItem("Settings", self._on_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._on_quit),
        )

        self._icon = pystray.Icon(
            name="WhisperTyping",
            icon=icon_image,
            title="WhisperTyping - Voice Typing",
            menu=menu,
        )

        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()
        logger.info("System tray icon started")

    def _create_icon(self, color: str) -> Image.Image:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Circle background
        draw.ellipse([4, 4, 60, 60], fill=color)
        # Microphone shape (simplified)
        draw.rounded_rectangle([24, 14, 40, 36], radius=6, fill="white")
        draw.arc([18, 26, 46, 50], start=0, end=180, fill="white", width=3)
        draw.line([32, 50, 32, 56], fill="white", width=3)
        draw.line([24, 56, 40, 56], fill="white", width=2)
        return img

    def update_icon(self, state: str):
        if not self._icon:
            return
        if state == "recording":
            self._icon.icon = self._create_icon("#FF4444")
            self._icon.title = "WhisperTyping - Recording..."
        elif state == "processing":
            self._icon.icon = self._create_icon("#FFAA00")
            self._icon.title = "WhisperTyping - Transcribing..."
        else:
            self._icon.icon = self._create_icon("#4287f5")
            self._icon.title = "WhisperTyping - Ready"

    def _on_show(self, icon, item):
        if self.on_show_window:
            self.on_show_window()

    def _on_settings(self, icon, item):
        if self.on_settings:
            self.on_settings()

    def _on_history(self, icon, item):
        if self.on_history:
            self.on_history()

    def _on_quit(self, icon, item):
        icon.stop()
        if self.on_quit:
            self.on_quit()

    def stop(self):
        if self._icon:
            self._icon.stop()
