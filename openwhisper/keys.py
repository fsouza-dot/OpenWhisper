"""Shared key name mappings used across the application.

This module provides a single source of truth for key name → key code
mappings, avoiding duplication across hotkey, insertion, and platform
modules.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pynput.keyboard import Key

# Friendly key names used in the UI and settings
STANDARD_KEY_NAMES = frozenset({
    "enter", "return", "tab", "escape", "esc", "space",
    "backspace", "delete", "up", "down", "left", "right",
    "home", "end", "pageup", "pagedown",
    "f1", "f2", "f3", "f4", "f5", "f6",
    "f7", "f8", "f9", "f10", "f11", "f12",
    "f13", "f14", "f15", "f16", "f17", "f18",
    "f19", "f20", "f21", "f22", "f23", "f24",
})


def get_pynput_key(key_name: str) -> "Key | None":
    """Map a friendly key name to a pynput Key.

    Returns None if the key name is not recognized.
    Single character keys should be handled separately.
    """
    from pynput.keyboard import Key

    _PYNPUT_KEY_MAP: dict[str, Key] = {
        "enter": Key.enter,
        "return": Key.enter,
        "tab": Key.tab,
        "escape": Key.esc,
        "esc": Key.esc,
        "space": Key.space,
        "backspace": Key.backspace,
        "delete": Key.delete,
        "up": Key.up,
        "down": Key.down,
        "left": Key.left,
        "right": Key.right,
        "home": Key.home,
        "end": Key.end,
        "pageup": Key.page_up,
        "pagedown": Key.page_down,
        "f1": Key.f1, "f2": Key.f2, "f3": Key.f3,
        "f4": Key.f4, "f5": Key.f5, "f6": Key.f6,
        "f7": Key.f7, "f8": Key.f8, "f9": Key.f9,
        "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
        "f13": Key.f13, "f14": Key.f14, "f15": Key.f15,
        "f16": Key.f16, "f17": Key.f17, "f18": Key.f18,
        "f19": Key.f19, "f20": Key.f20,
    }
    return _PYNPUT_KEY_MAP.get(key_name.lower())


# Windows Virtual Key codes
# Only used on Windows platform
WIN32_VK_CODES: dict[str, int] = {
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "escape": 0x1B,
    "esc": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "space": 0x20,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "v": 0x56,  # Used for Ctrl+V paste
}

# Windows modifier virtual key codes
WIN32_VK_CONTROL = 0x11
WIN32_VK_SHIFT = 0x10
WIN32_VK_ALT = 0x12  # VK_MENU
WIN32_VK_LWIN = 0x5B
WIN32_VK_RWIN = 0x5C
