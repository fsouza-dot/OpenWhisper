"""Windows text insertion implementation."""
from __future__ import annotations

import time
from typing import Optional

import pyperclip

from ...logging_setup import get_logger
from ...protocols import TextInsertionProvider

log = get_logger("platform.windows.insertion")


class WindowsInserter(TextInsertionProvider):
    """Windows text insertion via clipboard + SendInput Ctrl+V."""

    def __init__(
        self,
        restore_clipboard: bool = True,
        use_clipboard: bool = True,
    ):
        self._restore = restore_clipboard
        self._use_clipboard = use_clipboard

    @property
    def restore_clipboard(self) -> bool:
        return self._restore

    @restore_clipboard.setter
    def restore_clipboard(self, value: bool) -> None:
        self._restore = value

    def insert(self, text: str) -> None:
        """Insert text at the cursor position."""
        if not text:
            return

        log.info("insert: starting (%d chars)", len(text))

        # Save clipboard if needed
        old_clipboard: Optional[str] = None
        if self._restore:
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                old_clipboard = None

        try:
            # Write to clipboard
            pyperclip.copy(text)
            log.info("insert: clipboard write ok")

            if self._use_clipboard:
                # Small delay to ensure clipboard is ready
                time.sleep(0.03)

                # Import here to avoid circular imports
                from . import _send_paste_windows
                _send_paste_windows()
                log.info("insert: paste sent")

                # Wait for paste to complete
                time.sleep(0.05)

        finally:
            # Restore clipboard
            if self._restore and old_clipboard is not None:
                time.sleep(0.1)
                try:
                    pyperclip.copy(old_clipboard)
                except Exception:
                    pass

    def press_key(self, key: str) -> None:
        """Press a special key."""
        from . import _send_key_windows
        _send_key_windows(key)
