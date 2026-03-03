import io
import time
import threading
import logging
from typing import Optional

from core.stt_engine import STTEngine, TranscriptionResult

logger = logging.getLogger(__name__)


class LocalSTTEngine(STTEngine):
    """Local transcription using faster-whisper with CUDA/CPU support."""

    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._loading = False
        self._load_event = threading.Event()

    def _ensure_model_loaded(self):
        if self._model is not None:
            return
        if self._loading:
            # Wait for the model to finish loading (up to 120s)
            logger.info("Waiting for model to finish loading...")
            self._load_event.wait(timeout=120)
            if self._model is not None:
                return
            raise RuntimeError("Model loading timed out")

        self._loading = True
        self._load_event.clear()
        try:
            from faster_whisper import WhisperModel

            logger.info(
                f"Loading faster-whisper model '{self.model_size}' "
                f"on {self.device} with {self.compute_type}"
            )
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("Model loaded successfully")
        except Exception as e:
            # Try falling back to CPU if CUDA fails
            if self.device == "cuda":
                logger.warning(f"CUDA load failed: {e}, falling back to CPU")
                self.device = "cpu"
                self.compute_type = "int8"
                try:
                    from faster_whisper import WhisperModel

                    self._model = WhisperModel(
                        self.model_size,
                        device="cpu",
                        compute_type="int8",
                    )
                    logger.info("Model loaded on CPU (fallback)")
                    return
                except Exception as e2:
                    logger.error(f"CPU fallback also failed: {e2}")
                    raise
            raise
        finally:
            self._loading = False
            self._load_event.set()

    def transcribe(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        self._ensure_model_loaded()

        start_time = time.time()
        audio_file = io.BytesIO(audio_data)

        kwargs = {
            "beam_size": 5,
            "vad_filter": True,
            "vad_parameters": {
                "min_silence_duration_ms": 500,
            },
        }
        if language and language != "auto":
            kwargs["language"] = language

        segments, info = self._model.transcribe(audio_file, **kwargs)

        # Collect all segment texts
        full_text = " ".join(segment.text.strip() for segment in segments)

        processing_time = time.time() - start_time
        detected_lang = info.language if info.language else (language or "en")

        return TranscriptionResult(
            text=full_text.strip(),
            language=detected_lang,
            confidence=info.language_probability if info.language_probability else 0.0,
            duration_seconds=info.duration if info.duration else 0.0,
            processing_time_seconds=processing_time,
        )

    def is_available(self) -> bool:
        try:
            self._ensure_model_loaded()
            return self._model is not None
        except Exception:
            return False

    def get_name(self) -> str:
        return f"faster-whisper ({self.model_size}, {self.device})"
