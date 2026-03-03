from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from config.constants import RTL_LANGUAGES


@dataclass
class TranscriptionResult:
    text: str
    language: str
    confidence: float
    duration_seconds: float
    processing_time_seconds: float

    @property
    def is_rtl(self) -> bool:
        return self.language in RTL_LANGUAGES


class STTEngine(ABC):
    """Abstract base class for speech-to-text engines."""

    @abstractmethod
    def transcribe(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass
