"""Windows platform implementation."""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes
from typing import Optional

from .. import Platform, PlatformType
from ...keys import WIN32_VK_CODES, WIN32_VK_CONTROL, WIN32_VK_SHIFT, WIN32_VK_ALT, WIN32_VK_LWIN, WIN32_VK_RWIN
from ...logging_setup import get_logger
from ...protocols import TextInsertionProvider
from .insertion import WindowsInserter
from .startup import is_startup_enabled, set_startup_enabled
from .win32_input import INPUT, KEYEVENTF_KEYUP, make_key_input, send_input

log = get_logger("platform.windows")

# Windows messages for clipboard operations
WM_PASTE = 0x0302


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

    def supports_startup(self) -> bool:
        """Windows supports auto-start via registry."""
        return True

    def is_startup_enabled(self) -> bool:
        """Check if OpenWhisper is set to run at Windows startup."""
        return is_startup_enabled()

    def set_startup_enabled(self, enabled: bool) -> bool:
        """Enable or disable startup with Windows."""
        return set_startup_enabled(enabled)


# --------------------------------------------------------------------------
# Win32 SendInput implementation
# --------------------------------------------------------------------------

# Timing constants
MODIFIER_RELEASE_DELAY = 0.02  # 20ms
FOCUS_SETTLE_DELAY = 0.03  # 30ms for window focus to settle


def _send_paste_windows() -> None:
    """Send paste command to the foreground window.

    Strategy: Check if the focused window is a Scintilla control (used by Notepad++).
    If so, use WM_PASTE. Otherwise, use SendInput Ctrl+V.
    """
    _force_release_modifiers()
    time.sleep(MODIFIER_RELEASE_DELAY)

    user32 = ctypes.windll.user32

    # Get foreground window
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        log.warning("No foreground window found")
        _send_ctrl_v()
        return

    # Small delay to ensure window is ready
    time.sleep(FOCUS_SETTLE_DELAY)

    # Check if we should use WM_PASTE (for Scintilla-based editors)
    if _should_use_wm_paste(user32, hwnd):
        if _try_send_wm_paste(user32, hwnd):
            return

    # Default: use SendInput Ctrl+V
    _send_ctrl_v()


def _should_use_wm_paste(user32, hwnd) -> bool:
    """Check if the focused control needs WM_PASTE (e.g., Scintilla)."""
    try:
        target_thread_id = user32.GetWindowThreadProcessId(hwnd, None)
        current_thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        if target_thread_id and target_thread_id != current_thread_id:
            if user32.AttachThreadInput(current_thread_id, target_thread_id, True):
                try:
                    focused = user32.GetFocus()
                    if focused:
                        # Get window class name
                        class_name = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(focused, class_name, 256)
                        class_str = class_name.value.lower()
                        # Scintilla is used by Notepad++, SciTE, and other editors
                        if "scintilla" in class_str:
                            return True
                finally:
                    user32.AttachThreadInput(current_thread_id, target_thread_id, False)
    except Exception:
        pass
    return False


def _try_send_wm_paste(user32, hwnd) -> bool:
    """Send WM_PASTE to the focused control. Returns True if successful."""
    try:
        target_thread_id = user32.GetWindowThreadProcessId(hwnd, None)
        current_thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        if target_thread_id and target_thread_id != current_thread_id:
            if user32.AttachThreadInput(current_thread_id, target_thread_id, True):
                try:
                    focused = user32.GetFocus()
                    target = focused if focused else hwnd
                    user32.SendMessageW(target, WM_PASTE, 0, 0)
                    return True
                finally:
                    user32.AttachThreadInput(current_thread_id, target_thread_id, False)
    except Exception as exc:
        log.debug("WM_PASTE failed: %s", exc)
    return False


def _send_ctrl_v() -> None:
    """Send Ctrl+V via SendInput."""
    sent = send_input(
        make_key_input(WIN32_VK_CONTROL, up=False),
        make_key_input(WIN32_VK_CODES["v"], up=False),
        make_key_input(WIN32_VK_CODES["v"], up=True),
        make_key_input(WIN32_VK_CONTROL, up=True),
    )
    if sent != 4:
        log.warning("SendInput rejected events (%d/4), GetLastError=%d",
                   sent, ctypes.windll.kernel32.GetLastError())


def _send_key_windows(key: str) -> None:
    """Send a single keypress via SendInput."""
    vk = WIN32_VK_CODES.get(key.lower())
    if vk is None:
        log.warning("Unknown key: %s", key)
        return

    send_input(
        make_key_input(vk, up=False),
        make_key_input(vk, up=True),
    )


def _force_release_modifiers() -> None:
    """Release modifier keys that might be held from the hotkey."""
    try:
        user32 = ctypes.windll.user32
        for vk in (WIN32_VK_ALT, WIN32_VK_CONTROL, WIN32_VK_SHIFT, WIN32_VK_LWIN, WIN32_VK_RWIN):
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    except Exception as exc:
        log.debug("Modifier release failed: %s", exc)
