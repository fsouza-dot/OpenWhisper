"""Windows platform implementation."""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes
from typing import Optional

from ..  import Platform, PlatformType
from ...logging_setup import get_logger
from ...protocols import TextInsertionProvider
from .insertion import WindowsInserter

log = get_logger("platform.windows")


class WindowsPlatform(Platform):
    """Windows-specific platform implementation."""

    platform_type = PlatformType.windows

    def create_inserter(
        self,
        restore_clipboard: bool = True,
        use_clipboard: bool = True,
    ) -> TextInsertionProvider:
        """Create a Windows text inserter."""
        return WindowsInserter(
            restore_clipboard=restore_clipboard,
            use_clipboard=use_clipboard,
        )

    def get_foreground_app(self) -> Optional[str]:
        """Get the foreground application name using Win32 API."""
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            hwnd = user32.GetForegroundWindow()
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value
            )
            if not handle:
                return None

            buf = ctypes.create_unicode_buffer(512)
            size = ctypes.c_ulong(len(buf))
            ok = kernel32.QueryFullProcessImageNameW(
                handle, 0, buf, ctypes.byref(size)
            )
            kernel32.CloseHandle(handle)

            if not ok:
                return None

            return buf.value.split("\\")[-1]
        except Exception:
            return None

    def send_key(self, key: str) -> None:
        """Send a keypress using Win32 SendInput."""
        _send_key_windows(key)

    def send_paste(self) -> None:
        """Send Ctrl+V using Win32 SendInput."""
        _send_paste_windows()


# --------------------------------------------------------------------------
# Win32 SendInput implementation
# --------------------------------------------------------------------------

# Virtual key codes
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12  # Alt
VK_LWIN = 0x5B
VK_RWIN = 0x5C

VK_MAP = {
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
    "v": 0x56,
}

# SendInput constants
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002

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


def _make_key_input(vk: int, up: bool = False) -> INPUT:
    """Create an INPUT struct for a key event."""
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki = KEYBDINPUT(
        wVk=vk,
        wScan=0,
        dwFlags=KEYEVENTF_KEYUP if up else 0,
        time=0,
        dwExtraInfo=0,
    )
    return inp


def _send_paste_windows() -> None:
    """Send Ctrl+V via SendInput."""
    # Release any held modifiers first to avoid interference
    _force_release_modifiers()
    time.sleep(0.05)

    user32 = ctypes.windll.user32
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT

    events = (INPUT * 4)(
        _make_key_input(VK_CONTROL, up=False),
        _make_key_input(VK_MAP["v"], up=False),
        _make_key_input(VK_MAP["v"], up=True),
        _make_key_input(VK_CONTROL, up=True),
    )
    sent = user32.SendInput(4, events, ctypes.sizeof(INPUT))
    if sent != 4:
        log.warning("SendInput rejected events (%d/4), GetLastError=%d",
                   sent, ctypes.windll.kernel32.GetLastError())


def _send_key_windows(key: str) -> None:
    """Send a single keypress via SendInput."""
    vk = VK_MAP.get(key.lower())
    if vk is None:
        log.warning("Unknown key: %s", key)
        return

    user32 = ctypes.windll.user32
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT

    events = (INPUT * 2)(
        _make_key_input(vk, up=False),
        _make_key_input(vk, up=True),
    )
    user32.SendInput(2, events, ctypes.sizeof(INPUT))


def _force_release_modifiers() -> None:
    """Release modifier keys that might be held from the hotkey."""
    try:
        user32 = ctypes.windll.user32
        for vk in (VK_MENU, VK_CONTROL, VK_SHIFT, VK_LWIN, VK_RWIN):
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    except Exception as exc:
        log.debug("Modifier release failed: %s", exc)
