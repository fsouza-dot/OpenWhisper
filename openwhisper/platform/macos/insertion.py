"""macOS text insertion: clipboard write + Cmd+V via CGEvent."""
from __future__ import annotations

from ..base_inserter import BaseInserter


class MacOSInserter(BaseInserter):
    @property
    def _platform_name(self) -> str:
        return "macos"

    def _send_paste(self) -> None:
        from .. import get_platform
        get_platform().send_paste()

    def _send_key(self, key: str) -> None:
        from .. import get_platform
        get_platform().send_key(key)
