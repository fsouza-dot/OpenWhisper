"""macOS text insertion implementation."""
from __future__ import annotations

from ..base_inserter import BaseInserter


class MacOSInserter(BaseInserter):
    """macOS text insertion via clipboard + Cmd+V."""

    @property
    def _platform_name(self) -> str:
        return "macos"

    def _send_paste(self) -> None:
        """Send Cmd+V via pynput."""
        from .. import get_platform
        get_platform().send_paste()

    def _send_key(self, key: str) -> None:
        """Send a key press via pynput."""
        from .. import get_platform
        get_platform().send_key(key)
