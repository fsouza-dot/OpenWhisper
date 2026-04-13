"""Shared UI state object. A single instance is owned by the app and
passed to every UI component. Uses Qt signals so widgets can react
without polling.
"""
from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QObject, Signal


class Phase(str, Enum):
    idle = "idle"
    recording = "recording"
    transcribing = "transcribing"
    cleaning = "cleaning"
    inserting = "inserting"
    error = "error"


class UIState(QObject):
    phaseChanged = Signal(Phase, str)  # phase, message
    livePreviewChanged = Signal(str)
    lastInsertedChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._phase = Phase.idle
        self._message = ""
        self._live_preview = ""
        self._last_inserted = ""

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def message(self) -> str:
        return self._message

    def set_phase(self, phase: Phase, message: str = "") -> None:
        self._phase = phase
        self._message = message
        self.phaseChanged.emit(phase, message)

    def set_live_preview(self, text: str) -> None:
        self._live_preview = text
        self.livePreviewChanged.emit(text)

    def set_last_inserted(self, text: str) -> None:
        self._last_inserted = text
        self.lastInsertedChanged.emit(text)

    def phase_title(self) -> str:
        return {
            Phase.idle: "Idle",
            Phase.recording: "Listening…",
            Phase.transcribing: "Transcribing…",
            Phase.cleaning: "Polishing…",
            Phase.inserting: "Pasting…",
            Phase.error: f"Error: {self._message}",
        }[self._phase]
