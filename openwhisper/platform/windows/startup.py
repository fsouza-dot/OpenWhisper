"""Windows startup registry management.

Handles adding/removing OpenWhisper from Windows startup via the registry.
"""
from __future__ import annotations

import sys
import winreg
from pathlib import Path

from ...logging_setup import get_logger

log = get_logger("platform.windows.startup")

# Registry key for current user startup programs
STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "OpenWhisper"


def get_executable_path() -> str:
    """Get the path to the current executable."""
    if getattr(sys, "frozen", False):
        # Running as compiled executable (PyInstaller)
        return sys.executable
    else:
        # Running as script - use pythonw to avoid console window
        return f'"{sys.executable}" "{Path(__file__).parents[3] / "main.py"}"'


def is_startup_enabled() -> bool:
    """Check if OpenWhisper is set to run at startup."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            winreg.KEY_READ,
        ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        log.warning("Failed to check startup status: %s", exc)
        return False


def set_startup_enabled(enabled: bool) -> bool:
    """Enable or disable startup with Windows.

    Returns True if the operation succeeded.
    """
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                exe_path = get_executable_path()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
                log.info("Added OpenWhisper to startup: %s", exe_path)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    log.info("Removed OpenWhisper from startup")
                except FileNotFoundError:
                    pass  # Already removed
        return True
    except OSError as exc:
        log.error("Failed to %s startup: %s", "enable" if enabled else "disable", exc)
        return False
