"""Typed settings models + JSON persistence.

Pydantic gives us validation, defaults, and round-trip JSON serialization
for free. The store is intentionally dumb: load on init, save on every
`update`. Good enough for an app where settings change a few times a day.
"""
from __future__ import annotations

import json
import threading
import uuid
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .config import settings_file_path
from .logging_setup import get_logger

log = get_logger("settings")


class DictationMode(str, Enum):
    verbatim = "verbatim"
    polished = "polished"


class STTProviderKind(str, Enum):
    whisper = "whisper"
    groq = "groq"


class HotkeyMode(str, Enum):
    push_to_talk = "push_to_talk"
    toggle = "toggle"


class PasteBehavior(str, Enum):
    simulate_paste = "simulate_paste"
    clipboard_only = "clipboard_only"


class HotkeyBinding(BaseModel):
    """A single global hotkey chord.

    ``key`` is the pynput key name, e.g. "space", "f9", "a". ``modifiers``
    is a list of canonical modifier names: "ctrl", "alt", "shift", "cmd".
    Storage is platform-agnostic; the keyboard label shown to the user is
    computed at display time (``Cmd``/``⌘`` on macOS, ``Win`` on Windows,
    ``Super`` on Linux).
    """
    key: str = "space"
    modifiers: List[str] = Field(default_factory=lambda: ["alt"])

    @field_validator("modifiers")
    @classmethod
    def _canonicalize_modifiers(cls, value: List[str]) -> List[str]:
        from .hotkey.display import canonical_modifier
        out: list[str] = []
        for entry in value:
            canon = canonical_modifier(entry)
            if canon is None:
                log.warning("Dropping unknown hotkey modifier: %r", entry)
                continue
            if canon not in out:
                out.append(canon)
        return out

    def pynput_hotkey_string(self) -> str:
        """Render to pynput's global hotkey format, e.g. "<alt>+<space>"."""
        parts: list[str] = []
        for mod in self.modifiers:
            parts.append(f"<{mod}>")
        key = self.key
        if len(key) > 1:
            key = f"<{key}>"
        parts.append(key)
        return "+".join(parts)

    def display(self) -> str:
        """Human-friendly label rendered for the current platform."""
        from .hotkey.display import format_chord
        return format_chord(self.modifiers, self.key)


class DictionaryEntry(BaseModel):
    """Personal dictionary entry for STT hints.

    Security: Field lengths are constrained to prevent DoS via large settings.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), max_length=64)
    term: str = Field(max_length=200)
    aliases: List[str] = Field(default_factory=list, max_length=20)
    case_sensitive: bool = False

    @field_validator("aliases")
    @classmethod
    def validate_aliases(cls, v: List[str]) -> List[str]:
        return [a[:200] for a in v[:20]]  # Security: limit alias count and length


class Snippet(BaseModel):
    """Text expansion snippet.

    Security: Field lengths are constrained to prevent DoS via large settings.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), max_length=64)
    trigger: str = Field(max_length=100)
    replacement: str = Field(max_length=10000)  # Allow longer replacements (e.g., templates)
    trigger_is_phrase: bool = False


class AppSettings(BaseModel):
    """Application settings with security constraints.

    Security: All string and list fields have length limits to prevent DoS
    attacks via maliciously crafted settings files.
    """
    input_device: Optional[str] = Field(default=None, max_length=500)
    # ISO 639-1 codes the user wants whisper to transcribe. A single entry
    # forces that language; multiple entries enable auto-detection.
    languages: List[str] = Field(default_factory=lambda: ["en"], max_length=10)
    hotkeys: List[HotkeyBinding] = Field(default_factory=lambda: [HotkeyBinding()], max_length=10)
    hotkey_mode: HotkeyMode = HotkeyMode.push_to_talk
    dictation_mode: DictationMode = DictationMode.polished
    stt_provider: STTProviderKind = STTProviderKind.whisper
    whisper_model_size: str = Field(default="small.en", max_length=50)
    whisper_compute_type: str = Field(default="int8", max_length=50)
    groq_model: str = Field(default="whisper-large-v3-turbo", max_length=100)
    paste_behavior: PasteBehavior = PasteBehavior.simulate_paste
    restore_clipboard: bool = True
    dictionary: List[DictionaryEntry] = Field(default_factory=list, max_length=500)
    snippets: List[Snippet] = Field(default_factory=list, max_length=200)
    save_audio_history: bool = False
    history_size: int = Field(default=20, ge=1, le=100)
    confirm_destructive_commands: bool = True
    auto_start: bool = False

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: List[str]) -> List[str]:
        # Security: limit language codes to reasonable length
        return [lang[:10] for lang in v[:10]]

    @model_validator(mode="before")
    @classmethod
    def _migrate_hotkey(cls, data):
        """Accept legacy settings that stored a single `hotkey` field."""
        if not isinstance(data, dict):
            return data
        if "hotkeys" not in data and "hotkey" in data:
            old = data.pop("hotkey")
            if isinstance(old, dict):
                data["hotkeys"] = [
                    {
                        "key": old.get("key", "space"),
                        "modifiers": old.get("modifiers", ["alt"]),
                    }
                ]
                if "hotkey_mode" not in data and "mode" in old:
                    data["hotkey_mode"] = old["mode"]
        return data

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def default(cls) -> "AppSettings":
        return cls()


class SettingsStore:
    """Thread-safe JSON-on-disk settings."""

    def __init__(self, file_path: Path | None = None):
        self._path: Path = file_path or settings_file_path()
        self._lock = threading.RLock()
        self._settings: AppSettings = self._load()
        self._listeners: list[Callable[[AppSettings], None]] = []

    @property
    def path(self) -> Path:
        return self._path

    @property
    def settings(self) -> AppSettings:
        with self._lock:
            return self._settings

    def update(self, mutate: Callable[[AppSettings], AppSettings]) -> AppSettings:
        """Apply a pure transformation and persist."""
        with self._lock:
            self._settings = mutate(self._settings)
            self._save()
            new = self._settings
        for listener in list(self._listeners):
            try:
                listener(new)
            except Exception as exc:  # pragma: no cover
                log.warning("Settings listener error: %s", exc)
        return new

    def replace(self, new: AppSettings) -> None:
        self.update(lambda _: new)

    def subscribe(self, listener: Callable[[AppSettings], None]) -> Callable[[], None]:
        """Subscribe to settings changes. Returns an unsubscribe function."""
        self._listeners.append(listener)
        def unsubscribe() -> None:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass
        return unsubscribe

    # ------------------------------------------------------------- persistence

    # Security: Maximum settings file size to prevent DoS
    MAX_SETTINGS_SIZE = 1024 * 1024  # 1 MB

    def _load(self) -> AppSettings:
        if not self._path.exists():
            return AppSettings.default()
        try:
            # Security: Check file size before reading
            file_size = self._path.stat().st_size
            if file_size > self.MAX_SETTINGS_SIZE:
                log.warning("Settings file too large (%d bytes), using defaults", file_size)
                return AppSettings.default()
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return AppSettings.model_validate(raw)
        except Exception as exc:
            log.warning("Settings file unreadable, using defaults: %s", exc)
            return AppSettings.default()

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            # Atomic write: write to temp file first, then rename
            temp_path = self._path.with_suffix(".tmp")
            temp_path.write_text(self._settings.to_json(), encoding="utf-8")
            temp_path.replace(self._path)
        except Exception as exc:
            log.error("Failed to save settings: %s", exc)
