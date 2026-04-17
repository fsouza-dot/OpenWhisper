"""Win32 SendInput structures and helpers.

This module provides the ctypes structures needed for Windows SendInput API,
shared between the main platform module and any other code that needs to
synthesize keyboard input.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

from ...keys import get_scan_code

# SendInput constants
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_EXTENDEDKEY = 0x0001

# ULONG_PTR is pointer-sized (4 on 32-bit, 8 on 64-bit)
ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    """Mouse input structure - needed for correct union size."""
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    """Keyboard input structure."""
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    """Hardware input structure."""
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTunion(ctypes.Union):
    """Union of all input types - must include all for correct sizing."""
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    """Windows INPUT structure for SendInput."""
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _INPUTunion),
    ]


def make_key_input(vk: int, up: bool = False) -> INPUT:
    """Create an INPUT struct for a key event.

    Includes scan codes for compatibility with modern Windows apps
    like the new Notepad which may ignore pure virtual key input.
    """
    scan = get_scan_code(vk)
    flags = 0
    if up:
        flags |= KEYEVENTF_KEYUP

    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki = KEYBDINPUT(
        wVk=vk,
        wScan=scan,
        dwFlags=flags,
        time=0,
        dwExtraInfo=0,
    )
    return inp


def send_input(*events: INPUT) -> int:
    """Send keyboard input events via SendInput.

    Returns the number of events successfully sent.
    """
    user32 = ctypes.windll.user32
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT

    n = len(events)
    arr = (INPUT * n)(*events)
    return user32.SendInput(n, arr, ctypes.sizeof(INPUT))
