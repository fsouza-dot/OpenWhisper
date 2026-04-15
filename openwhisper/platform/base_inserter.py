"""Base class for platform-specific text insertion.

Provides a template method pattern for clipboard-based text insertion
that is shared across all platforms.
"""
from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from typing import Optional

import pyperclip

from ..logging_setup import get_logger
from ..protocols import TextInsertionProvider

# Timing constants (security: minimize clipboard exposure)
CLIPBOARD_SETTLE_DELAY = 0.03  # Time for clipboard to be ready
PASTE_COMPLETE_DELAY = 0.05   # Time for paste to complete
CLIPBOARD_RESTORE_DELAY = 0.05  # Minimal delay before restoring


class BaseInserter(TextInsertionProvider, ABC):
    """Base class for text insertion via clipboard + paste simulation.

    Subclasses must implement:
    - _send_paste(): Platform-specific paste command (Ctrl+V or Cmd+V)
    - _send_key(key): Platform-specific key press
    """

    def __init__(
        self,
        restore_clipboard: bool = True,
        use_clipboard: bool = True,
    ):
        self._restore = restore_clipboard
        self._use_clipboard = use_clipboard
        self._lock = threading.Lock()
        self._log = get_logger(f"platform.{self._platform_name}.insertion")

    @property
    @abstractmethod
    def _platform_name(self) -> str:
        """Platform name for logging (e.g., 'windows', 'linux', 'macos')."""
        ...

    @property
    def restore_clipboard(self) -> bool:
        return self._restore

    @restore_clipboard.setter
    def restore_clipboard(self, value: bool) -> None:
        self._restore = value

    @abstractmethod
    def _send_paste(self) -> None:
        """Send the platform-specific paste command."""
        ...

    @abstractmethod
    def _send_key(self, key: str) -> None:
        """Send a platform-specific key press."""
        ...

    def insert(self, text: str) -> None:
        """Insert text at the cursor position via clipboard."""
        if not text:
            return

        with self._lock:
            self._log.info("insert: starting (%d chars)", len(text))

            # Save clipboard if needed
            previous: Optional[str] = None
            if self._restore:
                try:
                    previous = pyperclip.paste()
                except Exception:
                    pass

            # Write to clipboard
            pyperclip.copy(text)
            self._log.info("insert: clipboard write ok")

            if self._use_clipboard:
                time.sleep(CLIPBOARD_SETTLE_DELAY)
                self._send_paste()
                self._log.info("insert: paste sent")
                time.sleep(PASTE_COMPLETE_DELAY)

            # Restore clipboard in background thread (non-blocking)
            if previous is not None:
                self._schedule_clipboard_restore(previous)

    def _schedule_clipboard_restore(self, previous: str) -> None:
        """Restore clipboard content in a background thread."""
        def _restore() -> None:
            time.sleep(CLIPBOARD_RESTORE_DELAY)
            try:
                pyperclip.copy(previous)
            except Exception:
                pass
        threading.Thread(target=_restore, daemon=True).start()

    def press_key(self, key: str) -> None:
        """Press a special key."""
        self._send_key(key)
