"""Linux text insertion implementation."""
from __future__ import annotations

from ..base_inserter import BaseInserter


class LinuxInserter(BaseInserter):
    """Linux text insertion via clipboard + pynput/xdotool Ctrl+V."""

    @property
    def _platform_name(self) -> str:
        return "linux"

    def _send_paste(self) -> None:
        """Send Ctrl+V via pynput or xdotool."""
        from .. import get_platform
        get_platform().send_paste()

    def _send_key(self, key: str) -> None:
        """Send a key press via pynput."""
        from .. import get_platform
        get_platform().send_key(key)
