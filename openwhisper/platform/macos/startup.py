"""Launch-at-login support via per-user LaunchAgent.

Writes ``~/Library/LaunchAgents/com.openwhisper.app.plist`` and asks
``launchctl`` to load it. Removing the agent disables autostart.
"""
from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path

from ...config import BUNDLE_ID
from ...logging_setup import get_logger

log = get_logger("platform.macos.startup")

PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{BUNDLE_ID}.plist"


def _program_arguments() -> list[str]:
    """Return the argv launchd should run.

    For frozen .app builds the executable lives at
    ``OpenWhisper.app/Contents/MacOS/OpenWhisper`` and ``sys.executable``
    points to it. For dev runs we fall back to invoking the current
    Python interpreter with the same script.
    """
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, os.path.abspath(sys.argv[0])]


def is_enabled() -> bool:
    return PLIST_PATH.exists()


def enable() -> bool:
    try:
        PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "Label": BUNDLE_ID,
            "ProgramArguments": _program_arguments(),
            "RunAtLoad": True,
            "ProcessType": "Interactive",
        }
        with PLIST_PATH.open("wb") as f:
            plistlib.dump(payload, f)
        # Best-effort load; if launchctl complains because it's already
        # loaded, that's fine.
        subprocess.run(
            ["launchctl", "load", "-w", str(PLIST_PATH)],
            check=False,
            capture_output=True,
        )
        log.info("Launch agent enabled at %s", PLIST_PATH)
        return True
    except Exception as exc:
        log.warning("Failed to enable launch agent: %s", exc)
        return False


def disable() -> bool:
    try:
        if PLIST_PATH.exists():
            subprocess.run(
                ["launchctl", "unload", "-w", str(PLIST_PATH)],
                check=False,
                capture_output=True,
            )
            PLIST_PATH.unlink()
            log.info("Launch agent disabled")
        return True
    except Exception as exc:
        log.warning("Failed to disable launch agent: %s", exc)
        return False
