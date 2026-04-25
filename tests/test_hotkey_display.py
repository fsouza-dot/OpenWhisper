from __future__ import annotations

import pytest

from openwhisper.hotkey.display import canonical_modifier, format_chord
from openwhisper.settings import HotkeyBinding


# ---------------------------- canonical_modifier ----------------------------

@pytest.mark.parametrize(
    "raw,canon",
    [
        ("ctrl", "ctrl"),
        ("Control", "ctrl"),
        ("CONTROL", "ctrl"),
        ("alt", "alt"),
        ("Option", "alt"),
        ("opt", "alt"),
        ("shift", "shift"),
        ("Shift", "shift"),
        ("cmd", "cmd"),
        ("Command", "cmd"),
        ("Win", "cmd"),
        ("super", "cmd"),
        ("meta", "cmd"),
        ("  cmd  ", "cmd"),
    ],
)
def test_canonical_modifier_aliases(raw, canon):
    assert canonical_modifier(raw) == canon


@pytest.mark.parametrize("bad", ["", "fn", "windows", "hyper", "bogus", None, 42])
def test_canonical_modifier_rejects_unknown(bad):
    assert canonical_modifier(bad) is None


# -------------------------- format_chord on macOS ---------------------------

def test_mac_no_modifiers(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    assert format_chord([], "space") == "Space"


def test_mac_option_space(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    assert format_chord(["alt"], "space") == "⌥Space"


def test_mac_canonical_order(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    # Modifiers given out of order; display should reorder to ⌃⌥⇧⌘.
    assert format_chord(["cmd", "shift"], "z") == "⇧⌘Z"
    assert format_chord(["shift", "ctrl", "cmd", "alt"], "a") == "⌃⌥⇧⌘A"


def test_mac_arrow_glyphs(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    assert format_chord(["alt"], "left") == "⌥←"
    assert format_chord(["cmd"], "up") == "⌘↑"


def test_mac_drops_unknown_modifier(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    assert format_chord(["cmd", "bogus"], "z") == "⌘Z"


# -------------------------- format_chord on Windows -------------------------

def test_windows_word_form(monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")
    assert format_chord(["ctrl", "shift"], "z") == "Ctrl + Shift + Z"


def test_windows_renders_cmd_as_win(monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")
    assert format_chord(["cmd"], "space") == "Win + Space"


# --------------------------- format_chord on Linux --------------------------

def test_linux_renders_cmd_as_super(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    assert format_chord(["cmd"], "space") == "Super + Space"


def test_linux_word_form(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    assert format_chord(["ctrl", "alt"], "delete") == "Ctrl + Alt + Delete"


# ------------------------ HotkeyBinding integration -------------------------

def test_binding_validator_canonicalizes_aliases():
    b = HotkeyBinding(key="space", modifiers=["Win", "Option"])
    assert b.modifiers == ["cmd", "alt"]


def test_binding_validator_drops_unknown():
    b = HotkeyBinding(key="z", modifiers=["cmd", "bogus", "shift"])
    assert b.modifiers == ["cmd", "shift"]


def test_binding_validator_dedupes():
    b = HotkeyBinding(key="z", modifiers=["cmd", "Command", "CMD"])
    assert b.modifiers == ["cmd"]


def test_binding_display_uses_platform(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    assert HotkeyBinding(key="space", modifiers=["alt"]).display() == "⌥Space"
    monkeypatch.setattr("sys.platform", "win32")
    assert HotkeyBinding(key="space", modifiers=["alt"]).display() == "Alt + Space"
