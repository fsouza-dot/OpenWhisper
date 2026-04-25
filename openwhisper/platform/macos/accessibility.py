"""macOS Accessibility (AX) permission helpers.

Hotkey capture and synthetic key injection both require the app to be
listed and enabled in System Settings -> Privacy & Security -> Accessibility.
We surface the OS prompt the first time the app launches so the user is
not stuck wondering why hotkeys silently do nothing.
"""
from __future__ import annotations

from ...logging_setup import get_logger

log = get_logger("platform.macos.accessibility")


def is_trusted() -> bool:
    """Return True if the running process is granted Accessibility access."""
    try:
        from ApplicationServices import AXIsProcessTrusted
        return bool(AXIsProcessTrusted())
    except Exception as exc:
        log.warning("AXIsProcessTrusted failed: %s", exc)
        return False


def prompt_for_trust() -> bool:
    """Check trust, showing the system grant dialog if not yet trusted.

    Returns the trust state at the moment of the call. The dialog itself
    is non-blocking — the user grants permission later in System Settings
    and must restart the app for it to take effect.
    """
    try:
        from ApplicationServices import (
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )
        options = {kAXTrustedCheckOptionPrompt: True}
        return bool(AXIsProcessTrustedWithOptions(options))
    except Exception as exc:
        log.warning("AXIsProcessTrustedWithOptions failed: %s", exc)
        return is_trusted()
