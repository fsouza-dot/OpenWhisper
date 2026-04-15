"""Local speech-to-text via `faster-whisper`.

Why faster-whisper:
- Uses CTranslate2 under the hood, so it runs whisper at 3-5× realtime
  on CPU with `int8` quantization — fast enough on any modern laptop.
- Automatically uses CUDA if available, zero config.
- Handles model download + caching automatically on first use.
- Stable Python API, no C-FFI babysitting.

We lazily construct the model on first transcription so the app starts
instantly — the ~460 MB `small.en` download only happens when the user
first presses the hotkey.
"""
from __future__ import annotations

import threading
from typing import List, Optional

from ..errors import ModelMissing, TranscriptionFailed
from ..logging_setup import get_logger
from ..protocols import AudioBuffer, Transcript, TranscriptSegment

log = get_logger("stt.whisper")


class FasterWhisperProvider:
    identifier = "faster-whisper"

    def __init__(
        self,
        model_size: str = "small.en",
        compute_type: str = "int8",
        device: str = "auto",
        languages: Optional[List[str]] = None,
    ):
        self.languages: List[str] = list(languages) if languages else ["en"]
        # The `.en` model variants only speak English. If the user has
        # enabled any non-English language, drop the `.en` suffix to pull
        # the multilingual model of the same size.
        if model_size.endswith(".en") and any(lang != "en" for lang in self.languages):
            log.info("Multilingual languages enabled; switching %s → %s",
                     model_size, model_size[:-3])
            model_size = model_size[:-3]
        self.model_size = model_size
        self.compute_type = compute_type
        # int8 / int8_float* are CPU-only kernels in CTranslate2. If we let
        # device="auto" pick CUDA on a machine with an NVIDIA GPU, the model
        # constructs OK but blows up at encode time looking for cuBLAS DLLs
        # that the bundled .exe does not ship. Lock to CPU in that case.
        if device == "auto" and compute_type.startswith("int8"):
            device = "cpu"
        self.device = device
        self._model = None
        self._model_lock = threading.Lock()
        self._load_error: Optional[str] = None

    @property
    def is_available(self) -> bool:
        # We can't prove availability until we try to load the model, but
        # we can at least report a prior load failure.
        return self._load_error is None

    def warmup(self) -> None:
        """Preload the model so the first hotkey press doesn't eat the
        ~2-5 s download/JIT cost. Safe to call from any thread."""
        try:
            self._ensure_model()
        except Exception as exc:
            log.warning("Whisper warmup failed: %s", exc)

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        with self._model_lock:
            if self._model is not None:
                return
            try:
                from faster_whisper import WhisperModel  # local import — heavy
                log.info("Loading faster-whisper model=%s device=%s compute=%s",
                         self.model_size, self.device, self.compute_type)
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                )
                self._load_error = None
                log.info("Whisper model loaded")
            except ImportError as exc:
                self._load_error = str(exc)
                raise ModelMissing(
                    "faster-whisper is not installed. Run `pip install faster-whisper`."
                ) from exc
            except Exception as exc:
                self._load_error = str(exc)
                raise TranscriptionFailed(
                    f"Could not load whisper model '{self.model_size}': {exc}"
                ) from exc

    def transcribe(self, audio: AudioBuffer, dictionary_hints: List[str]) -> Transcript:
        if audio.samples.size == 0:
            return Transcript(text="")

        self._ensure_model()
        assert self._model is not None

        # faster-whisper wants a 1D float32 numpy array at 16 kHz, which is
        # exactly what AudioRecorder produces.
        initial_prompt = None
        if dictionary_hints:
            # Biases decoding toward the user's personal vocabulary.
            initial_prompt = "Vocabulary: " + ", ".join(dictionary_hints[:64])

        # NOTE: faster-whisper returns a *lazy* generator from .transcribe().
        # The actual encode/decode work runs as you iterate. We must wrap the
        # iteration in the try, not just the call, otherwise runtime errors
        # (e.g. cuBLAS DLL missing during encode) escape uncaught.
        segments: list[TranscriptSegment] = []
        text_parts: list[str] = []
        # If exactly one language is configured, force it (fastest + most
        # accurate). Otherwise let whisper auto-detect from the audio.
        forced_language = self.languages[0] if len(self.languages) == 1 else None
        try:
            # Speed knobs for push-to-talk dictation:
            # - beam_size=1: greedy decode, 2-3x faster than beam=5 with
            #   <1% WER impact on clean speech.
            # - vad_filter=False: the hotkey already bounds the clip, so
            #   a second Silero pass over the whole audio is wasted work.
            # - without_timestamps=True: skips the timestamp-token decoding
            #   branch; we don't use segment timings anywhere.
            segments_iter, info = self._model.transcribe(
                audio.samples,
                language=forced_language,
                beam_size=1,
                vad_filter=False,
                without_timestamps=True,
                initial_prompt=initial_prompt,
                condition_on_previous_text=False,
            )
            for seg in segments_iter:
                segments.append(TranscriptSegment(text=seg.text, start=seg.start, end=seg.end))
                text_parts.append(seg.text)
        except Exception as exc:
            # Drop the (possibly broken) cached model so the next attempt
            # rebuilds from scratch instead of hanging in a half-dead state.
            self._model = None
            self._load_error = str(exc)
            raise TranscriptionFailed(str(exc)) from exc

        text = " ".join(p.strip() for p in text_parts).strip()

        # faster-whisper does not return a single scalar confidence; use a
        # proxy: 1.0 by default, lowered if transcript is empty.
        confidence = 1.0 if text else 0.0
        log.info("Transcribed %.2fs in language=%s (%d chars)",
                 audio.duration, getattr(info, "language", "?"), len(text))
        return Transcript(text=text, confidence=confidence, segments=segments)
