import numpy as np
import sounddevice as sd
import threading
import queue
import io
import wave
import time
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Records audio from the microphone using sounddevice callbacks."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device_index: Optional[int] = None,
        on_level_update: Optional[Callable[[float], None]] = None,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_index = device_index if device_index != -1 else None
        self.on_level_update = on_level_update

        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._is_recording = False
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        self._queue_lock = threading.Lock()

        self._chunk_thread: Optional[threading.Thread] = None
        self._on_chunk_ready: Optional[Callable[[bytes], None]] = None
        self._silence_ms: int = 500

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            logger.warning(f"Audio callback status: {status}")
        if self._is_recording:
            self._audio_queue.put(indata.copy())
            if self.on_level_update:
                rms = float(np.sqrt(np.mean(indata ** 2)))
                self.on_level_update(rms)

    def _chunks_to_wav(self, chunks: list) -> bytes:
        """Convert a list of numpy audio chunks to WAV bytes."""
        audio_data = np.concatenate(chunks, axis=0)
        audio_int16 = (audio_data * 32767).astype(np.int16)
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())
        return buffer.getvalue()

    def _chunk_loop(self):
        """VAD-based chunking: emit chunks on natural silence boundaries."""
        SILENCE_RMS = 0.008  # amplitude below this = silence
        silence_threshold_samples = int(self.sample_rate * (self._silence_ms / 1000))
        min_speech_samples = int(self.sample_rate * 0.8)   # min 0.8 sec speech to emit
        max_chunk_samples = int(self.sample_rate * 15.0)   # force emit after 15 sec

        buffer: list[np.ndarray] = []
        silence_samples = 0
        speech_samples = 0

        while self._is_recording:
            try:
                chunk = self._audio_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            rms = float(np.sqrt(np.mean(chunk ** 2)))
            buffer.append(chunk)

            if rms < SILENCE_RMS:
                silence_samples += len(chunk)
            else:
                silence_samples = 0
                speech_samples += len(chunk)

            total_samples = sum(len(c) for c in buffer)
            emit_on_pause = (silence_samples >= silence_threshold_samples
                             and speech_samples >= min_speech_samples)
            emit_on_max = total_samples >= max_chunk_samples

            if emit_on_pause or emit_on_max:
                wav = self._chunks_to_wav(buffer)
                buffer = []
                silence_samples = 0
                speech_samples = 0
                if self._on_chunk_ready:
                    self._on_chunk_ready(wav)

        # Drain remaining queue items
        while not self._audio_queue.empty():
            try:
                buffer.append(self._audio_queue.get_nowait())
            except queue.Empty:
                break

        # Emit final buffer if there's enough speech
        if buffer and speech_samples >= min_speech_samples // 2 and self._on_chunk_ready:
            self._on_chunk_ready(self._chunks_to_wav(buffer))

    def start_recording(
        self,
        on_chunk_ready: Optional[Callable[[bytes], None]] = None,
        silence_ms: int = 500,
    ):
        with self._lock:
            if self._is_recording:
                return

            # Clear stale data
            while not self._audio_queue.empty():
                self._audio_queue.get_nowait()

            self._on_chunk_ready = on_chunk_ready
            self._silence_ms = silence_ms
            self._is_recording = True
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                device=self.device_index,
                blocksize=1024,
                callback=self._audio_callback,
            )
            self._stream.start()

            if on_chunk_ready:
                self._chunk_thread = threading.Thread(
                    target=self._chunk_loop, daemon=True
                )
                self._chunk_thread.start()

            logger.info("Recording started")

    def stop_recording(self) -> Optional[bytes]:
        with self._lock:
            if not self._is_recording:
                return None
            self._is_recording = False
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

        # Wait for chunk thread to finish its current iteration
        if self._chunk_thread and self._chunk_thread.is_alive():
            self._chunk_thread.join(timeout=2.0)
        self._chunk_thread = None
        self._on_chunk_ready = None

        # Drain remaining audio (tail after last chunk)
        with self._queue_lock:
            chunks = []
            while not self._audio_queue.empty():
                try:
                    chunks.append(self._audio_queue.get_nowait())
                except queue.Empty:
                    break

        if not chunks:
            return None

        return self._chunks_to_wav(chunks)

    @staticmethod
    def list_devices() -> list[dict]:
        devices = sd.query_devices()
        input_devices = []
        seen_names = set()
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                name = dev["name"]
                if name in seen_names:
                    continue
                seen_names.add(name)
                input_devices.append({
                    "index": i,
                    "name": name,
                    "channels": dev["max_input_channels"],
                    "sample_rate": dev["default_samplerate"],
                })
        return input_devices

    def cleanup(self):
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._is_recording = False
