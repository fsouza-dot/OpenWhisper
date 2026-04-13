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

from pydantic import BaseModel, Field, model_validator

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


class CommandModeSetting(str, Enum):
    always_on = "always_on"
    modifier_held = "modifier_held"
    wake_phrase = "wake_phrase"


class PasteBehavior(str, Enum):
    simulate_paste = "simulate_paste"
    clipboard_only = "clipboard_only"


class HotkeyBinding(BaseModel):
    """A single global hotkey chord.

    `key` is the pynput key name, e.g. "space", "f9", "a".
    `modifiers` is a list of "ctrl", "alt", "shift", "cmd" (cmd = Win key).
    """
    key: str = "space"
    modifiers: List[str] = Field(default_factory=lambda: ["alt"])

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
        """Human-friendly label, e.g. 'Alt + Space'."""
        parts = [m.capitalize() if m != "cmd" else "Win" for m in self.modifiers]
        parts.append(self.key.upper() if len(self.key) == 1 else self.key.capitalize())
        return " + ".join(parts)


class DictionaryEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    term: str
    aliases: List[str] = Field(default_factory=list)
    case_sensitive: bool = False


class Snippet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trigger: str
    replacement: str
    trigger_is_phrase: bool = False


class AppSettings(BaseModel):
    input_device: Optional[str] = None  # device name, None = system default
    # ISO 639-1 codes the user wants whisper to transcribe. A single entry
    # forces that language; multiple entries enable auto-detection.
    languages: List[str] = Field(default_factory=lambda: ["en"])
    hotkeys: List[HotkeyBinding] = Field(default_factory=lambda: [HotkeyBinding()])
    hotkey_mode: HotkeyMode = HotkeyMode.push_to_talk
    dictation_mode: DictationMode = DictationMode.polished
    stt_provider: STTProviderKind = STTProviderKind.whisper
    whisper_model_size: str = "small.en"  # tiny.en | base.en | small.en | medium.en
    whisper_compute_type: str = "int8"    # int8 | int8_float16 | float16 | float32
    groq_model: str = "whisper-large-v3-turbo"
    paste_behavior: PasteBehavior = PasteBehavior.simulate_paste
    restore_clipboard: bool = True
    command_mode: CommandModeSetting = CommandModeSetting.always_on
    dictionary: List[DictionaryEntry] = Field(default_factory=list)
    snippets: List[Snippet] = Field(default_factory=list)
    save_audio_history: bool = False
    history_size: int = 20
    confirm_destructive_commands: bool = True

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

    def subscribe(self, listener: Callable[[AppSettings], None]) -> None:
        self._listeners.append(listener)

    # ------------------------------------------------------------- persistence

    def _load(self) -> AppSettings:
        if not self._path.exists():
            return AppSettings.default()
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return AppSettings.model_validate(raw)
        except Exception as exc:
            log.warning("Settings file unreadable, using defaults: %s", exc)
            return AppSettings.default()

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(self._settings.to_json(), encoding="utf-8")
        except Exception as exc:
            log.error("Failed to save settings: %s", exc)
