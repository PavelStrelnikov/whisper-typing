import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MAX_HISTORY_ITEMS = 200


@dataclass
class HistoryEntry:
    text: str
    language: str
    timestamp: str  # ISO format
    duration_seconds: float = 0.0
    processing_time_seconds: float = 0.0

    @staticmethod
    def now(text: str, language: str, duration: float = 0.0,
            processing_time: float = 0.0) -> "HistoryEntry":
        return HistoryEntry(
            text=text,
            language=language,
            timestamp=datetime.now().isoformat(),
            duration_seconds=duration,
            processing_time_seconds=processing_time,
        )


class TranscriptionHistory:
    """Persists transcription history to a JSON file."""

    def __init__(self, path: Optional[Path] = None):
        if path is None:
            appdata = Path.home() / "AppData" / "Roaming" / "WhisperTyping"
            appdata.mkdir(parents=True, exist_ok=True)
            path = appdata / "history.json"
        self._path = path
        self._entries: list[HistoryEntry] = []
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._entries = [
                    HistoryEntry(**item) for item in data
                ]
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.warning(f"Failed to load history: {e}")
                self._entries = []

    def _save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(
                    [asdict(e) for e in self._entries],
                    f, ensure_ascii=False, indent=2,
                )
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def add(self, entry: HistoryEntry):
        self._entries.insert(0, entry)
        # Trim to max size
        if len(self._entries) > MAX_HISTORY_ITEMS:
            self._entries = self._entries[:MAX_HISTORY_ITEMS]
        self._save()

    def get_all(self) -> list[HistoryEntry]:
        return list(self._entries)

    def clear(self):
        self._entries.clear()
        self._save()

    def __len__(self) -> int:
        return len(self._entries)
