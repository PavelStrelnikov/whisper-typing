import io
import time
import logging
from typing import Optional

from core.stt_engine import STTEngine, TranscriptionResult

logger = logging.getLogger(__name__)


class CloudSTTEngine(STTEngine):
    """Cloud transcription using the OpenAI Whisper API."""

    def __init__(self, api_key: str, model: str = "whisper-1"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.api_key)

    def transcribe(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        self._ensure_client()

        start_time = time.time()

        audio_file = io.BytesIO(audio_data)
        audio_file.name = "recording.wav"

        kwargs = {
            "model": self.model,
            "file": audio_file,
            "response_format": "verbose_json",
        }
        if language and language != "auto":
            kwargs["language"] = language

        response = self._client.audio.transcriptions.create(**kwargs)

        processing_time = time.time() - start_time

        detected_lang = getattr(response, "language", language or "en")
        text = response.text if hasattr(response, "text") else str(response)
        duration = getattr(response, "duration", 0.0)

        return TranscriptionResult(
            text=text.strip(),
            language=detected_lang,
            confidence=1.0,
            duration_seconds=float(duration),
            processing_time_seconds=processing_time,
        )

    def is_available(self) -> bool:
        return bool(self.api_key)

    def get_name(self) -> str:
        return f"OpenAI Whisper API ({self.model})"
