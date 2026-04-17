"""Convenience launcher so you can `python run.py` from the repo root
without installing the package first.

For frozen builds, this also handles missing dependency errors gracefully.
"""
from __future__ import annotations

import sys


def _show_error_dialog(title: str, message: str) -> None:
    """Show a native Windows error dialog without any dependencies."""
    if sys.platform != "win32":
        print(f"ERROR: {title}\n{message}", file=sys.stderr)
        return

    import ctypes
    MB_OK = 0x0
    MB_ICONERROR = 0x10
    ctypes.windll.user32.MessageBoxW(0, message, title, MB_OK | MB_ICONERROR)


def _check_dependencies() -> bool:
    """Check if critical dependencies can be loaded. Returns True if OK."""
    errors = []

    # Test numpy (most common failure point due to C extensions)
    try:
        import numpy
    except ImportError as e:
        error_str = str(e).lower()
        if "dll" in error_str or "c-extension" in error_str or "libopenblas" in error_str:
            errors.append(
                "NumPy C-extensions could not be loaded.\n\n"
                "This usually means the Microsoft Visual C++ Redistributable is not installed."
            )
        else:
            errors.append(f"NumPy import failed: {e}")

    # Test PySide6 (Qt framework)
    try:
        from PySide6 import QtCore
    except ImportError as e:
        errors.append(f"PySide6 (Qt) import failed: {e}")

    if errors:
        message = (
            "OpenWhisper cannot start due to missing system components.\n\n"
            + "\n\n".join(errors) +
            "\n\n"
            "To fix this, please install the Microsoft Visual C++ Redistributable:\n\n"
            "1. Visit: https://aka.ms/vs/17/release/vc_redist.x64.exe\n"
            "2. Download and run the installer\n"
            "3. Restart OpenWhisper\n\n"
            "If you installed via MSI, try repairing or reinstalling OpenWhisper."
        )
        _show_error_dialog("OpenWhisper - Missing Dependencies", message)
        return False

    return True


if __name__ == "__main__":
    # For frozen builds, check dependencies first and show friendly error
    if getattr(sys, "frozen", False):
        if not _check_dependencies():
            sys.exit(1)

    # Now safe to import the full app
    from openwhisper.app import run
    raise SystemExit(run())
