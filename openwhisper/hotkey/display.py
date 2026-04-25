"""Human-friendly hotkey chord rendering.

Storage is always lowercase canonical names (``ctrl``, ``alt``, ``shift``,
``cmd``) so a settings file roundtrips identically across platforms. The
*display* of a chord is platform-specific:

- macOS: native glyphs in Apple's canonical order ``⌃⌥⇧⌘`` followed by
  the key (e.g. ``⌘⇧Z``). Arrow keys are also rendered as glyphs.
- Windows: word form joined with `` + ``; ``cmd`` shows as ``Win``.
- Linux: word form joined with `` + ``; ``cmd`` shows as ``Super``.
"""
from __future__ import annotations

import sys

_ALIASES: dict[str, str] = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "option": "alt",
    "opt": "alt",
    "shift": "shift",
    "cmd": "cmd",
    "command": "cmd",
    "win": "cmd",
    "super": "cmd",
    "meta": "cmd",
}

# Apple's canonical modifier order: Control, Option, Shift, Command.
_MAC_ORDER: dict[str, int] = {"ctrl": 0, "alt": 1, "shift": 2, "cmd": 3}

_MAC_GLYPHS: dict[str, str] = {
    "ctrl": "⌃",
    "alt": "⌥",
    "shift": "⇧",
    "cmd": "⌘",
}

_MAC_KEY_GLYPHS: dict[str, str] = {
    "left": "←",
    "right": "→",
    "up": "↑",
    "down": "↓",
}

_OTHER_LABELS: dict[str, dict[str, str]] = {
    "win32": {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "cmd": "Win"},
    "linux": {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "cmd": "Super"},
}


def canonical_modifier(name: str) -> str | None:
    """Map any accepted modifier alias to its canonical name.

    Returns ``None`` for unknown values so callers (e.g. the
    ``HotkeyBinding`` validator) can drop them.
    """
    if not isinstance(name, str):
        return None
    return _ALIASES.get(name.strip().lower())


def _label_key(key: str, *, mac: bool) -> str:
    if mac and key in _MAC_KEY_GLYPHS:
        return _MAC_KEY_GLYPHS[key]
    if len(key) == 1:
        return key.upper()
    return key.capitalize()


def _platform_labels() -> dict[str, str]:
    if sys.platform.startswith("linux"):
        return _OTHER_LABELS["linux"]
    return _OTHER_LABELS["win32"]


def format_chord(modifiers: list[str], key: str) -> str:
    """Render a chord for the current platform.

    Modifiers should already be canonical; unknown values are skipped.
    """
    canon = [m for m in (canonical_modifier(x) for x in modifiers) if m]

    if sys.platform == "darwin":
        canon.sort(key=lambda m: _MAC_ORDER[m])
        glyphs = "".join(_MAC_GLYPHS[m] for m in canon)
        return f"{glyphs}{_label_key(key, mac=True)}"

    labels = _platform_labels()
    parts = [labels[m] for m in canon]
    parts.append(_label_key(key, mac=False))
    return " + ".join(parts)
