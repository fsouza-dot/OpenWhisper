"""Protocol definitions for every swappable subsystem.

Keeping these here — rather than nailing them down inside each concrete
module — makes the domain layer independent of faster-whisper,
pynput, etc. Tests can pass in fakes without importing any of them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Protocol, runtime_checkable

import numpy as np

# Note: DictationMode and other settings types are used directly by the
# cleanup pipeline rather than through these protocols.


# ------------------------------------------------------------- value objects

@dataclass
class AudioBuffer:
    """Mono 16 kHz Float32 audio. Everything in the app normalizes to this."""
    samples: np.ndarray  # shape: (N,), dtype: float32
    sample_rate: int = 16_000

    @property
    def duration(self) -> float:
        return float(len(self.samples)) / float(self.sample_rate)


@dataclass
class TranscriptSegment:
    text: str
    start: float
    end: float


@dataclass
class Transcript:
    text: str
    confidence: float = 1.0
    segments: List[TranscriptSegment] = field(default_factory=list)


@dataclass
class CleanupResult:
    cleaned: str
    command: Optional[str] = None   # DictationCommand.value, or None
    confidence: float = 1.0
    used_llm: bool = False
    model_used: Optional[str] = None


@dataclass
class CommandDecision:
    command: Optional[str]
    residual_text: str
    confidence: float


# ----------------------------------------------------------------- protocols

@runtime_checkable
class SpeechToTextProvider(Protocol):
    identifier: str
    is_available: bool

    def transcribe(self, audio: AudioBuffer, dictionary_hints: List[str]) -> Transcript: ...


@runtime_checkable
class TextInsertionProvider(Protocol):
    def insert(self, text: str) -> None: ...
    def press_key(self, key_name: str) -> None: ...


@runtime_checkable
class CommandInterpreting(Protocol):
    def interpret(self, text: str) -> CommandDecision: ...
