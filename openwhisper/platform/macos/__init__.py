"""macOS platform implementation (placeholder).

TODO: Implement macOS-specific functionality:
- Cmd+V paste simulation (not Ctrl+V)
- Foreground app detection via NSWorkspace
- Accessibility permissions handling
"""
from __future__ import annotations

from typing import Optional

from .. import Platform, PlatformType
from ...logging_setup import get_logger
from ...protocols import TextInsertionProvider

log = get_logger("platform.macos")


class MacOSPlatform(Platform):
    """macOS-specific platform implementation.

    NOTE: This is a placeholder. macOS support is not yet implemented.
    """

    platform_type = PlatformType.macos

    def __init__(self):
        log.warning("macOS support is not yet fully implemented")
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
        """Create a macOS text inserter."""
        from .insertion import MacOSInserter
        return MacOSInserter(
            restore_clipboard=restore_clipboard,
            use_clipboard=use_clipboard,
        )

    def get_foreground_app(self) -> Optional[str]:
        """Get the foreground application name.

        TODO: Use NSWorkspace.sharedWorkspace().frontmostApplication()
        """
        try:
            # Attempt to use AppKit if available
            from AppKit import NSWorkspace
            app = NSWorkspace.sharedWorkspace().frontmostApplication()
            return app.localizedName()
        except ImportError:
            pass
        except Exception:
            pass

        return None

    def send_key(self, key: str) -> None:
        """Send a keypress using pynput."""
        from pynput.keyboard import Key

        key_map = {
            "enter": Key.enter,
            "return": Key.enter,
            "tab": Key.tab,
            "escape": Key.esc,
            "esc": Key.esc,
            "backspace": Key.backspace,
            "delete": Key.delete,
            "space": Key.space,
            "up": Key.up,
            "down": Key.down,
            "left": Key.left,
            "right": Key.right,
            "home": Key.home,
            "end": Key.end,
            "pageup": Key.page_up,
            "pagedown": Key.page_down,
        }

        pynput_key = key_map.get(key.lower())
        if pynput_key is None:
            log.warning("Unknown key: %s", key)
            return

        kb = self._get_keyboard()
        kb.press(pynput_key)
        kb.release(pynput_key)

    def send_paste(self) -> None:
        """Send Cmd+V using pynput (macOS uses Cmd, not Ctrl)."""
        from pynput.keyboard import Key

        kb = self._get_keyboard()

        # macOS uses Cmd (Key.cmd) instead of Ctrl
        kb.press(Key.cmd)
        kb.press('v')
        kb.release('v')
        kb.release(Key.cmd)
