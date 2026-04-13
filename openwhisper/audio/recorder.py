"""Microphone capture via `sounddevice`.

We open an InputStream at 16 kHz mono Float32 — the native format every
local STT engine wants — so no resampling is needed downstream. Audio is
buffered in memory and only materialized into a single numpy array on
stop(). Nothing is ever written to disk.
"""
from __future__ import annotations

import threading
from typing import List, Optional

import numpy as np
import sounddevice as sd

from ..errors import MicrophoneUnavailable
from ..logging_setup import get_logger
from ..protocols import AudioBuffer

log = get_logger("audio")


SAMPLE_RATE = 16_000
CHANNELS = 1
BLOCK_SIZE = 1024


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
        self._device_name: Optional[str] = None

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def set_device(self, name: Optional[str]) -> None:
        self._device_name = name

    def start(self) -> None:
        if self._is_recording:
            return
        with self._lock:
            self._chunks.clear()
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
        except Exception as exc:
            log.error("Failed to start audio stream: %s", exc)
            raise MicrophoneUnavailable(str(exc)) from exc
        self._is_recording = True
        log.info("Recording started at %d Hz", SAMPLE_RATE)

    def stop(self) -> AudioBuffer:
        if not self._is_recording:
            return AudioBuffer(samples=np.zeros(0, dtype=np.float32))
        self._is_recording = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as exc:  # pragma: no cover
                log.warning("Error stopping stream: %s", exc)
            self._stream = None

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
        # indata is (frames, channels); we force mono by taking channel 0.
        chunk = indata[:, 0].copy() if indata.ndim == 2 else indata.copy()
        with self._lock:
            self._chunks.append(chunk)
