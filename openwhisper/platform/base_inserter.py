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
CLIPBOARD_SETTLE_DELAY = 0.05   # Wait for clipboard write to propagate before Ctrl+V
PASTE_COMPLETE_DELAY = 0.08     # Wait after Ctrl+V for the app to read the clipboard
CLIPBOARD_RESTORE_DELAY = 0.40  # Wait before restoring — conservative so slow apps finish reading
CLIPBOARD_VERIFY_RETRIES = 3    # Re-try clipboard write if verification fails
CLIPBOARD_VERIFY_RETRY_DELAY = 0.02  # Delay between retries (clipboard may be briefly locked)


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
        # Cancels the pending restore when a new insertion starts.
        self._restore_cancel = threading.Event()

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

            # Cancel any restore still pending from the previous insertion.
            self._restore_cancel.set()
            cancel = threading.Event()
            self._restore_cancel = cancel

            # Save clipboard if needed
            previous: Optional[str] = None
            if self._restore:
                try:
                    previous = pyperclip.paste()
                except Exception:
                    pass

            # Write to clipboard and verify — retries if the clipboard is
            # briefly locked by another process (common on Windows).
            if not self._write_clipboard_verified(text):
                self._log.error("insert: clipboard write failed after retries — aborting paste")
                return

            if self._use_clipboard:
                time.sleep(CLIPBOARD_SETTLE_DELAY)
                self._send_paste()
                self._log.info("insert: paste sent")
                time.sleep(PASTE_COMPLETE_DELAY)

            # Restore clipboard in background thread (non-blocking).
            if previous is not None:
                self._schedule_clipboard_restore(previous, expected=text, cancel=cancel)

    def _write_clipboard_verified(self, text: str) -> bool:
        """Write text to clipboard and read it back to confirm the write succeeded.

        Returns True if verified. Retries up to CLIPBOARD_VERIFY_RETRIES times
        to handle transient clipboard locks from other Windows processes.
        """
        for attempt in range(CLIPBOARD_VERIFY_RETRIES):
            try:
                pyperclip.copy(text)
                if pyperclip.paste() == text:
                    self._log.info("insert: clipboard write verified (attempt %d)", attempt + 1)
                    return True
                self._log.warning("insert: clipboard write not verified (attempt %d)", attempt + 1)
            except Exception as exc:
                self._log.warning("insert: clipboard error (attempt %d): %s", attempt + 1, exc)
            time.sleep(CLIPBOARD_VERIFY_RETRY_DELAY)
        return False

    def _schedule_clipboard_restore(self, previous: str, expected: str, cancel: threading.Event) -> None:
        """Restore clipboard content in a background thread.

        Waits CLIPBOARD_RESTORE_DELAY for the target app to finish reading the
        clipboard after Ctrl+V. If cancelled (new insertion started) or if the
        clipboard no longer contains our text (user already changed it), skips
        the restore.
        """
        def _restore() -> None:
            # cancel.wait() returns True if cancelled, False on timeout.
            if cancel.wait(timeout=CLIPBOARD_RESTORE_DELAY):
                return
            try:
                if pyperclip.paste() == expected:
                    pyperclip.copy(previous)
            except Exception:
                pass
        threading.Thread(target=_restore, daemon=True).start()

    def press_key(self, key: str) -> None:
        """Press a special key."""
        self._send_key(key)
