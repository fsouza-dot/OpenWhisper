"""Microphone capture via `sounddevice`.

We open an InputStream at 16 kHz mono Float32 — the native format every
local STT engine wants — so no resampling is needed downstream. Audio is
buffered in memory and only materialized into a single numpy array on
stop(). Nothing is ever written to disk.
"""
from __future__ import annotations

import threading
from typing import Callable, List, Optional

import numpy as np
import sounddevice as sd

from ..errors import MicrophoneUnavailable
from ..logging_setup import get_logger
from ..protocols import AudioBuffer

log = get_logger("audio")


SAMPLE_RATE = 16_000
CHANNELS = 1
BLOCK_SIZE = 1024
NUM_LEVEL_BANDS = 5  # Number of bars in the visualizer
RMS_GAIN_FACTOR = 20.0  # Scaling factor for RMS to make levels visible


def resolve_input_device(name: Optional[str]) -> Optional[int]:
    """Look up an input device index by name. Returns None for system default
    or if the named device is not currently connected."""
    if not name:
        return None
    try:
        for idx, dev in enumerate(sd.query_devices()):
            if dev.get("max_input_channels", 0) > 0 and dev.get("name") == name:
                return idx
    except Exception as exc:  # pragma: no cover
        log.warning("Failed to enumerate audio devices: %s", exc)
    log.warning("Configured input device not found: %s (using default)", name)
    return None


class AudioRecorder:
    def __init__(self) -> None:
        self._stream: sd.InputStream | None = None
        self._chunks: List[np.ndarray] = []
        self._lock = threading.Lock()
        self._is_recording = False
        self._stream_open = False
        self._device_name: Optional[str] = None
        self._on_levels: Optional[Callable[[List[float]], None]] = None

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def set_device(self, name: Optional[str]) -> None:
        if name == self._device_name:
            return
        self._device_name = name
        if self._stream_open:
            # Reopen with new device so next press uses it immediately.
            self.close_stream()
            try:
                self.open_stream()
            except MicrophoneUnavailable as exc:
                log.warning("Failed to reopen stream for new device: %s", exc)

    def open_stream(self) -> None:
        """Pre-initialize the audio stream once at startup.

        Calls start() then stop() so the WASAPI IAudioClient is already
        negotiated. Subsequent start() calls resume in ~5-30ms instead of
        the 50-300ms needed for a cold open.
        """
        if self._stream_open:
            return
        try:
            device = resolve_input_device(self._device_name)
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=BLOCK_SIZE,
                callback=self._on_audio,
                device=device,
            )
            self._stream.start()
            self._stream.stop()  # warm the WASAPI client; mic is released until next start()
            self._stream_open = True
            log.info("Audio stream pre-initialized at %d Hz (device=%s)", SAMPLE_RATE, self._device_name or "default")
        except Exception as exc:
            log.error("Failed to pre-initialize audio stream: %s", exc)
            raise MicrophoneUnavailable(str(exc)) from exc

    def close_stream(self) -> None:
        """Fully close the stream on app shutdown or device change."""
        self._stream_open = False
        self._is_recording = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as exc:  # pragma: no cover
                log.warning("Error closing stream: %s", exc)
            self._stream = None

    def set_levels_callback(self, callback: Optional[Callable[[List[float]], None]]) -> None:
        """Set callback to receive audio levels for visualization.

        Callback receives a list of NUM_LEVEL_BANDS floats (0.0-1.0).
        """
        self._on_levels = callback

    def start(self) -> None:
        if self._is_recording:
            return
        # If open_stream() was never called (e.g. in tests), open lazily.
        if not self._stream_open:
            self.open_stream()
        with self._lock:
            self._chunks.clear()
        try:
            self._stream.start()  # fast resume — WASAPI client already initialized
        except Exception as exc:
            log.error("Failed to resume audio stream: %s", exc)
            raise MicrophoneUnavailable(str(exc)) from exc
        self._is_recording = True
        log.info("Recording started")

    def stop(self) -> AudioBuffer:
        if not self._is_recording:
            return AudioBuffer(samples=np.zeros(0, dtype=np.float32))
        self._is_recording = False
        if self._stream is not None:
            try:
                self._stream.stop()  # pause; WASAPI client stays warm, mic indicator off
            except Exception as exc:  # pragma: no cover
                log.warning("Error stopping stream: %s", exc)

        with self._lock:
            chunks = self._chunks
            self._chunks = []

        if not chunks:
            samples = np.zeros(0, dtype=np.float32)
        else:
            samples = np.concatenate(chunks).astype(np.float32, copy=False).flatten()
        log.info("Recording stopped: %.2fs (%d samples)",
                 len(samples) / SAMPLE_RATE, len(samples))
        return AudioBuffer(samples=samples, sample_rate=SAMPLE_RATE)

    def _on_audio(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            log.debug("sounddevice status: %s", status)
        if not self._is_recording:
            return  # Stream is open but idle — discard frames.
        # indata is (frames, channels); we force mono by taking channel 0.
        chunk = indata[:, 0].copy() if indata.ndim == 2 else indata.copy()
        with self._lock:
            self._chunks.append(chunk)

        # Calculate audio levels for visualization
        if self._on_levels is not None:
            levels = self._calculate_levels(chunk)
            try:
                self._on_levels(levels)
            except Exception as exc:
                log.debug("Audio levels callback error: %s", exc)

    def _calculate_levels(self, chunk: np.ndarray) -> List[float]:
        """Calculate RMS levels for NUM_LEVEL_BANDS frequency-ish bands.

        We split the chunk into bands and calculate RMS for each.
        This gives a simple but effective audio visualizer.
        """
        chunk_len = len(chunk)
        band_size = chunk_len // NUM_LEVEL_BANDS
        levels: List[float] = []

        for i in range(NUM_LEVEL_BANDS):
            start = i * band_size
            end = start + band_size if i < NUM_LEVEL_BANDS - 1 else chunk_len
            band = chunk[start:end]

            # Calculate RMS (root mean square) for this band
            if len(band) > 0:
                rms = float(np.sqrt(np.mean(band ** 2)))
                # Scale and clamp to 0.0-1.0
                level = min(1.0, rms * RMS_GAIN_FACTOR)
            else:
                level = 0.0
            levels.append(level)

        return levels
