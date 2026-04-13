"""Filesystem paths and fixed constants.

Everything user-writable lives under %APPDATA%\\OpenWhisper on Windows.
On non-Windows hosts we fall back to ~/.local/share/OpenWhisper so tests
still run on CI / WSL.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "OpenWhisper"
BUNDLE_ID = "com.openwhisper.app"

# Keychain / Credential Manager constants.
KEYRING_SERVICE = "OpenWhisper"
KEYRING_GROQ_ACCOUNT = "groq_api_key"


def app_data_dir() -> Path:
    """Return the per-user data directory, creating it on first access."""
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        path = Path(base) / APP_NAME
    else:
        path = Path.home() / ".local" / "share" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_file_path() -> Path:
    return app_data_dir() / "settings.json"


def log_file_path() -> Path:
    return app_data_dir() / "openwhisper.log"


def asset_path(relative: str) -> Path:
    """Locate a bundled asset in both dev and PyInstaller-frozen runs."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        p = Path(base) / "assets" / relative
        if p.exists():
            return p
    # Dev run: repo root is two levels up from this file.
    return Path(__file__).resolve().parent.parent / "assets" / relative


def models_dir() -> Path:
    path = app_data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path
