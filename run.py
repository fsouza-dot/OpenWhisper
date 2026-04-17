"""Convenience launcher so you can `python run.py` from the repo root
without installing the package first.

For frozen builds, this also handles applying pending updates before
the main app loads (so no files are locked).
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _get_app_data_dir() -> Path:
    """Get app data directory without importing openwhisper modules."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", "")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return Path(base) / "OpenWhisper"


def _show_message(title: str, text: str, icon: int = 0x40) -> None:
    """Show a Windows message box. icon: 0x40=Info, 0x30=Warning, 0x10=Error."""
    if sys.platform != "win32":
        return
    import ctypes
    ctypes.windll.user32.MessageBoxW(0, text, title, icon)


def _ask_yes_no(title: str, text: str) -> bool:
    """Show a Yes/No dialog. Returns True if user clicked Yes."""
    if sys.platform != "win32":
        return True
    import ctypes
    result = ctypes.windll.user32.MessageBoxW(0, text, title, 0x24)  # Question + Yes/No
    return result == 6  # 6 = IDYES


def _apply_pending_update() -> bool:
    """Check for and apply pending update. Returns True if update was applied."""
    app_data = _get_app_data_dir()
    update_dir = app_data / "pending_update"
    marker = update_dir / "update_ready.txt"

    if not marker.exists():
        return False

    extract_dir = update_dir / "extracted"
    if not extract_dir.exists():
        shutil.rmtree(update_dir, ignore_errors=True)
        return False

    # Read pending version
    try:
        pending_version = marker.read_text(encoding="utf-8").strip()
    except Exception:
        pending_version = "new version"

    # Ask user for confirmation
    if not _ask_yes_no(
        "OpenWhisper Update",
        f"A downloaded update (v{pending_version}) is ready to install.\n\n"
        "Apply the update now?",
    ):
        # User declined - remove pending update
        shutil.rmtree(update_dir, ignore_errors=True)
        return False

    # Find exe directory
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
    else:
        # Development mode - don't apply updates
        shutil.rmtree(update_dir, ignore_errors=True)
        return False

    try:
        # Find source directory (might be nested in a single folder)
        source_dirs = list(extract_dir.iterdir())
        if len(source_dirs) == 1 and source_dirs[0].is_dir():
            source_dir = source_dirs[0]
        else:
            source_dir = extract_dir

        # Copy all files from update to exe directory
        for item in source_dir.iterdir():
            dest = exe_dir / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                if dest.exists():
                    dest.unlink()
                shutil.copy2(item, dest)

        # Clean up update directory
        shutil.rmtree(update_dir, ignore_errors=True)

        _show_message(
            "OpenWhisper Update",
            f"Update to v{pending_version} applied successfully!",
        )
        return True

    except Exception as exc:
        shutil.rmtree(update_dir, ignore_errors=True)
        _show_message(
            "OpenWhisper Update Failed",
            f"Failed to apply update: {exc}",
            0x10,  # Error icon
        )
        return False


if __name__ == "__main__":
    # Apply pending update before importing anything else
    # This ensures no files are locked
    if getattr(sys, "frozen", False):
        if _apply_pending_update():
            # Update was applied - restart to load the new code
            import subprocess
            subprocess.Popen(
                [sys.executable],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            sys.exit(0)

    # Now import and run the app
    from openwhisper.app import run
    raise SystemExit(run())
