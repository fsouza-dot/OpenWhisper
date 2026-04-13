"""Global hotkey manager using a low-level pynput keyboard listener.

We cannot use `pynput.keyboard.GlobalHotKeys` here because it only
reports presses, and push-to-talk mode requires both press and release
events. Instead we run a single `Listener` and track modifier state
manually, firing our callbacks when the set of active chords
transitions in/out of the fully-held state.

Supports multiple bindings simultaneously: press any registered chord
to start, release all of them to stop. Overlapping chords do not fire
duplicate events — the manager only reports the *first* activation and
the *final* deactivation in a contiguous run.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional, Set

from pynput import keyboard

from ..logging_setup import get_logger
from ..settings import HotkeyBinding

log = get_logger("hotkey")


# Modifier name → the set of pynput Keys that satisfy it.
_MODIFIER_MAP: dict[str, Set[keyboard.Key]] = {
    "ctrl":    {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r},
    "control": {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r},
    "alt":     {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr},
    "shift":   {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r},
    "cmd":     {keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r},
    "win":     {keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r},
}


_NAMED_KEYS: dict[str, keyboard.Key] = {
    "space": keyboard.Key.space,
    "tab": keyboard.Key.tab,
    "enter": keyboard.Key.enter,
    "esc": keyboard.Key.esc,
    "escape": keyboard.Key.esc,
    "f1": keyboard.Key.f1, "f2": keyboard.Key.f2, "f3": keyboard.Key.f3,
    "f4": keyboard.Key.f4, "f5": keyboard.Key.f5, "f6": keyboard.Key.f6,
    "f7": keyboard.Key.f7, "f8": keyboard.Key.f8, "f9": keyboard.Key.f9,
    "f10": keyboard.Key.f10, "f11": keyboard.Key.f11, "f12": keyboard.Key.f12,
}


class HotkeyEvent:
    PRESSED = "pressed"
    RELEASED = "released"


@dataclass
class _Chord:
    required_modifiers: List[Set[keyboard.Key]]
    target_key: object  # Key or KeyCode
    target_char: Optional[str]
    active: bool = False


class HotkeyManager:
    """Fires `on_event("pressed")` when any registered chord becomes
    active (and no other chord was already active), and
    `on_event("released")` when the last active chord releases.
    """

    def __init__(self) -> None:
        self.on_event: Optional[Callable[[str], None]] = None
        self._listener: Optional[keyboard.Listener] = None
        self._held: Set[object] = set()
        self._chords: List[_Chord] = []
        self._active_count = 0
        self._lock = threading.Lock()

    def register(self, bindings: Iterable[HotkeyBinding]) -> None:
        self.unregister()
        self._chords = [self._compile(b) for b in bindings]
        self._held = set()
        self._active_count = 0
        if not self._chords:
            log.warning("No hotkey bindings registered")
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.daemon = True
        self._listener.start()
        log.info(
            "Hotkeys registered: %s",
            ", ".join(b.pynput_hotkey_string() for b in bindings),
        )

    def unregister(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:  # pragma: no cover
                pass
            self._listener = None

    # ------------------------------------------------------------- internals

    def _compile(self, binding: HotkeyBinding) -> _Chord:
        mods: list[Set[keyboard.Key]] = []
        for name in binding.modifiers:
            variants = _MODIFIER_MAP.get(name.lower())
            if variants is None:
                log.warning("Unknown modifier: %s", name)
                continue
            mods.append(variants)

        target_key: object
        target_char: Optional[str] = None
        key_name = binding.key.lower()
        if key_name in _NAMED_KEYS:
            target_key = _NAMED_KEYS[key_name]
        elif len(key_name) == 1:
            target_key = keyboard.KeyCode.from_char(key_name)
            target_char = key_name
        else:
            log.warning("Unknown key name: %s — falling back to space", key_name)
            target_key = keyboard.Key.space
        return _Chord(
            required_modifiers=mods,
            target_key=target_key,
            target_char=target_char,
        )

    def _normalize(self, key) -> object:
        """Collapse left/right variants onto a canonical identity."""
        if isinstance(key, keyboard.KeyCode) and key.char:
            return key.char.lower()
        return key

    def _chord_held(self, chord: _Chord) -> bool:
        for variants in chord.required_modifiers:
            if not any(v in self._held for v in variants):
                return False
        if chord.target_char is not None:
            if chord.target_char not in self._held:
                return False
        else:
            if chord.target_key not in self._held:
                return False
        return True

    def _on_press(self, key) -> None:
        with self._lock:
            norm = self._normalize(key)
            self._held.add(norm)
            if key not in self._held:
                self._held.add(key)
            self._reconcile()

    def _on_release(self, key) -> None:
        with self._lock:
            norm = self._normalize(key)
            self._held.discard(norm)
            self._held.discard(key)
            self._reconcile()

    def _reconcile(self) -> None:
        """Update every chord's active flag and fire aggregate events."""
        prev_total = self._active_count
        new_total = 0
        for chord in self._chords:
            is_held = self._chord_held(chord)
            chord.active = is_held
            if is_held:
                new_total += 1
        self._active_count = new_total
        if prev_total == 0 and new_total > 0:
            self._fire(HotkeyEvent.PRESSED)
        elif prev_total > 0 and new_total == 0:
            self._fire(HotkeyEvent.RELEASED)

    def _fire(self, event: str) -> None:
        if self.on_event is None:
            return
        try:
            self.on_event(event)
        except Exception as exc:  # pragma: no cover
            log.exception("Hotkey callback failed: %s", exc)
