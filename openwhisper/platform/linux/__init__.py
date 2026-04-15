"""Linux platform implementation."""
from __future__ import annotations

import shutil
import subprocess
import time
from typing import Optional

from .. import Platform, PlatformType
from ...keys import get_pynput_key
from ...logging_setup import get_logger
from ...protocols import TextInsertionProvider
from .insertion import LinuxInserter

log = get_logger("platform.linux")


class LinuxPlatform(Platform):
    """Linux-specific platform implementation.

    Uses pynput for keyboard simulation, which works on X11.
    For Wayland, xdotool/ydotool may be needed as fallback.
    """

    platform_type = PlatformType.linux

    def __init__(self):
        self._has_xdotool = shutil.which("xdotool") is not None
        self._keyboard = None

    def _get_keyboard(self):
        """Lazy-load pynput keyboard controller."""
        if self._keyboard is None:
            from pynput.keyboard import Controller
            self._keyboard = Controller()
        return self._keyboard

    def create_inserter(
        self,
        restore_clipboard: bool = True,
        use_clipboard: bool = True,
    ) -> TextInsertionProvider:
        """Create a Linux text inserter."""
        return LinuxInserter(
            restore_clipboard=restore_clipboard,
            use_clipboard=use_clipboard,
        )

    def get_foreground_app(self) -> Optional[str]:
        """Get the foreground application name using xdotool."""
        if not self._has_xdotool:
            return None

        try:
            # Get active window ID
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        return None

    def send_key(self, key: str) -> None:
        """Send a keypress using pynput."""
        pynput_key = get_pynput_key(key)
        if pynput_key is None:
            log.warning("Unknown key: %s", key)
            return

        kb = self._get_keyboard()
        kb.press(pynput_key)
        kb.release(pynput_key)

    def send_paste(self) -> None:
        """Send Ctrl+V using pynput."""
        from pynput.keyboard import Key

        # Try xdotool first if available (more reliable on some systems)
        if self._has_xdotool:
            try:
                subprocess.run(
                    ["xdotool", "key", "ctrl+v"],
                    timeout=1,
                    check=True,
                )
                return
            except Exception:
                pass  # Fall back to pynput

        kb = self._get_keyboard()

        # Release any held modifiers first
        for mod in (Key.ctrl, Key.shift, Key.alt):
            try:
                kb.release(mod)
            except Exception:
                pass

        time.sleep(0.02)

        # Send Ctrl+V
        kb.press(Key.ctrl)
        kb.press('v')
        kb.release('v')
        kb.release(Key.ctrl)
