"""Domain-level exceptions. Using our own hierarchy lets the coordinator
present friendly error messages in the HUD without having to know about
every low-level library we depend on.
"""
from __future__ import annotations


class OpenWhisperError(Exception):
    """Base class for all app-specific errors."""


class MicrophoneUnavailable(OpenWhisperError):
    pass


class TranscriptionFailed(OpenWhisperError):
    pass


class CleanupFailed(OpenWhisperError):
    pass


class InsertionFailed(OpenWhisperError):
    pass


class ModelMissing(OpenWhisperError):
    pass


class ApiKeyMissing(OpenWhisperError):
    pass


class HotkeyRegistrationFailed(OpenWhisperError):
    pass
