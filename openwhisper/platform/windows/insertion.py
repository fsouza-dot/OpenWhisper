"""Windows text insertion implementation."""
from __future__ import annotations

from ..base_inserter import BaseInserter


class WindowsInserter(BaseInserter):
    """Windows text insertion via clipboard + SendInput Ctrl+V."""

    @property
    def _platform_name(self) -> str:
        return "windows"

    def _send_paste(self) -> None:
        """Send Ctrl+V via Win32 SendInput."""
        from . import _send_paste_windows
        _send_paste_windows()

    def _send_key(self, key: str) -> None:
        """Send a key press via Win32 SendInput."""
        from . import _send_key_windows
        _send_key_windows(key)
