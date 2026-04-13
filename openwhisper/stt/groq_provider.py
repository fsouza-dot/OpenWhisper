"""Cloud speech-to-text via Groq's OpenAI-compatible audio endpoint.

Why Groq: `whisper-large-v3-turbo` runs at ~216x realtime on Groq's
inference hardware, so a 5-second dictation typically finalizes in
well under a second — closing most of the gap with commercial
dictation tools while still costing roughly nothing ($0.04/hour).

We encode our in-memory Float32 samples to a 16-bit PCM WAV and POST
it as multipart/form-data using `httpx`.
"""
from __future__ import annotations

import io
import threading
import wave
from typing import Callable, List, Optional

import httpx
import numpy as np

from ..errors import ApiKeyMissing, TranscriptionFailed
from ..logging_setup import get_logger
from ..protocols import AudioBuffer, Transcript

log = get_logger("stt.groq")


GROQ_ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_MODEL = "whisper-large-v3-turbo"


class GroqWhisperProvider:
    identifier = "groq"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        languages: Optional[List[str]] = None,
        timeout: float = 30.0,
        on_usage: Optional[Callable[[float], None]] = None,
    ):
        if not api_key:
            raise ApiKeyMissing("Groq API key is empty")
        self.api_key = api_key
        self.model = model
        self.languages: List[str] = list(languages) if languages else ["en"]
        self._client = httpx.Client(timeout=timeout)
        self._load_error: Optional[str] = None
        self._lock = threading.Lock()
        self._on_usage = on_usage

    @property
    def is_available(self) -> bool:
        return self._load_error is None

    def warmup(self) -> None:
        """No-op: Groq is a stateless HTTP endpoint, nothing to preload."""
        return

    def transcribe(self, audio: AudioBuffer, dictionary_hints: List[str]) -> Transcript:
        if audio.samples.size == 0:
            return Transcript(text="")

        wav_bytes = _float32_to_wav_bytes(audio.samples, audio.sample_rate)

        forced_language = self.languages[0] if len(self.languages) == 1 else None

        data: dict[str, str] = {
            "model": self.model,
            # Plain text is ~10x smaller than JSON on the wire and we
            # only need the text here.
            "response_format": "text",
            "temperature": "0",
        }
        if forced_language:
            data["language"] = forced_language
        if dictionary_hints:
            # Groq's /audio/transcriptions accepts an OpenAI-style prompt
            # that biases decoding toward the listed terms.
            data["prompt"] = "Vocabulary: " + ", ".join(dictionary_hints[:64])

        files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            with self._lock:
                resp = self._client.post(
                    GROQ_ENDPOINT, headers=headers, data=data, files=files
                )
        except Exception as exc:
            self._load_error = str(exc)
            raise TranscriptionFailed(f"Groq request failed: {exc}") from exc

        if resp.status_code != 200:
            body = resp.text[:300]
            self._load_error = f"HTTP {resp.status_code}"
            raise TranscriptionFailed(
                f"Groq HTTP {resp.status_code}: {body}"
            )

        self._load_error = None
        if self._on_usage is not None:
            try:
                self._on_usage(audio.duration)
            except Exception:  # pragma: no cover
                pass
        text = resp.text.strip() if data["response_format"] == "text" else ""
        if not text and data["response_format"] != "text":
            # Fallback parse if we ever switch response_format back to json.
            try:
                text = (resp.json() or {}).get("text", "").strip()
            except Exception:
                text = ""

        log.info("Groq transcribed %.2fs text=%r", audio.duration, text[:80])
        return Transcript(
            text=text,
            confidence=1.0 if text else 0.0,
        )


def _float32_to_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    """Encode a mono Float32 array to a 16-bit PCM WAV blob."""
    if samples.dtype != np.float32:
        samples = samples.astype(np.float32, copy=False)
    # Clip then scale to int16.
    clipped = np.clip(samples, -1.0, 1.0)
    int16 = (clipped * 32767.0).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # int16 = 2 bytes
        wav.setframerate(sample_rate)
        wav.writeframes(int16.tobytes())
    return buf.getvalue()
