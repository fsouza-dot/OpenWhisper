"""Quartz CGEvent helpers for synthesizing keyboard input on macOS.

We post events to ``kCGHIDEventTap`` so they look like real hardware
input — that's what most apps (browsers, Electron, native AppKit) check
when filtering synthetic events. Higher taps (session/annotated-session)
are filtered by some hardened apps.
"""
from __future__ import annotations

from typing import Optional

# macOS virtual keycodes (Carbon/HIToolbox/Events.h kVK_*).
# Only the keys exposed via openwhisper.keys.STANDARD_KEY_NAMES are mapped.
KEYCODES: dict[str, int] = {
    "v": 0x09,
    "enter": 0x24,
    "return": 0x24,
    "tab": 0x30,
    "space": 0x31,
    "backspace": 0x33,
    "escape": 0x35,
    "esc": 0x35,
    "delete": 0x75,
    "left": 0x7B,
    "right": 0x7C,
    "down": 0x7D,
    "up": 0x7E,
    "home": 0x73,
    "end": 0x77,
    "pageup": 0x74,
    "pagedown": 0x79,
    "f1": 0x7A, "f2": 0x78, "f3": 0x63, "f4": 0x76,
    "f5": 0x60, "f6": 0x61, "f7": 0x62, "f8": 0x64,
    "f9": 0x65, "f10": 0x6D, "f11": 0x67, "f12": 0x6F,
    "f13": 0x69, "f14": 0x6B, "f15": 0x71, "f16": 0x6A,
    "f17": 0x40, "f18": 0x4F, "f19": 0x50, "f20": 0x5A,
}


def keycode_for(name: str) -> Optional[int]:
    return KEYCODES.get(name.lower())


def post_key(
    keycode: int,
    *,
    cmd: bool = False,
    shift: bool = False,
    alt: bool = False,
    ctrl: bool = False,
) -> None:
    """Synthesize a single keypress (down + up) at the HID event tap."""
    from Quartz import (
        CGEventCreateKeyboardEvent,
        CGEventPost,
        CGEventSetFlags,
        kCGEventFlagMaskCommand,
        kCGEventFlagMaskShift,
        kCGEventFlagMaskAlternate,
        kCGEventFlagMaskControl,
        kCGHIDEventTap,
    )

    flags = 0
    if cmd:
        flags |= kCGEventFlagMaskCommand
    if shift:
        flags |= kCGEventFlagMaskShift
    if alt:
        flags |= kCGEventFlagMaskAlternate
    if ctrl:
        flags |= kCGEventFlagMaskControl

    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up = CGEventCreateKeyboardEvent(None, keycode, False)
    if flags:
        CGEventSetFlags(down, flags)
        CGEventSetFlags(up, flags)
    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)


def post_paste() -> None:
    """Send Cmd+V at the HID event tap."""
    post_key(KEYCODES["v"], cmd=True)
