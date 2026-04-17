"""Auto-update system that checks GitHub releases for new versions.

Supports both portable (ZIP) and MSI installations. On update:
- Portable: Downloads ZIP, extracts to temp, replaces files on next launch
- MSI: Downloads MSI, runs installer silently
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import httpx

from . import __version__
from .config import app_data_dir
from .logging_setup import get_logger

log = get_logger("updater")

GITHUB_REPO = "fsouza-dot/OpenWhisper"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
UPDATE_CHECK_TIMEOUT = 10.0


@dataclass
class ReleaseInfo:
    version: str
    tag_name: str
    zip_url: Optional[str]
    msi_url: Optional[str]
    release_url: str
    release_notes: str


@dataclass
class UpdateResult:
    available: bool
    current_version: str
    latest_version: Optional[str] = None
    release_info: Optional[ReleaseInfo] = None
    error: Optional[str] = None


def parse_version(version_str: str) -> tuple:
    """Parse version string like '0.3.0' or 'v0.3.0' into comparable tuple."""
    v = version_str.lstrip("v").strip()
    parts = []
    for part in v.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer_version(current: str, latest: str) -> bool:
    """Check if latest version is newer than current."""
    return parse_version(latest) > parse_version(current)


def is_msi_installation() -> bool:
    """Detect if running from an MSI installation (vs portable)."""
    exe_path = Path(sys.executable)
    if exe_path.name.lower() == "python.exe":
        return False
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
    exe_str = str(exe_path).lower()
    return program_files.lower() in exe_str or program_files_x86.lower() in exe_str


def get_exe_directory() -> Path:
    """Get the directory containing the main executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def check_for_updates() -> UpdateResult:
    """Check GitHub for new releases. Returns UpdateResult with status."""
    current = __version__
    try:
        with httpx.Client(timeout=UPDATE_CHECK_TIMEOUT) as client:
            resp = client.get(
                GITHUB_API_URL,
                headers={"Accept": "application/vnd.github.v3+json"},
                follow_redirects=True,
            )
            if resp.status_code != 200:
                return UpdateResult(
                    available=False,
                    current_version=current,
                    error=f"GitHub API returned {resp.status_code}",
                )
            data = resp.json()

        tag_name = data.get("tag_name", "")
        latest_version = tag_name.lstrip("v")

        if not is_newer_version(current, latest_version):
            return UpdateResult(
                available=False,
                current_version=current,
                latest_version=latest_version,
            )

        zip_url = None
        msi_url = None
        for asset in data.get("assets", []):
            name = asset.get("name", "").lower()
            url = asset.get("browser_download_url", "")
            if name.endswith(".zip"):
                zip_url = url
            elif name.endswith(".msi"):
                msi_url = url

        release_info = ReleaseInfo(
            version=latest_version,
            tag_name=tag_name,
            zip_url=zip_url,
            msi_url=msi_url,
            release_url=data.get("html_url", ""),
            release_notes=data.get("body", ""),
        )

        return UpdateResult(
            available=True,
            current_version=current,
            latest_version=latest_version,
            release_info=release_info,
        )

    except httpx.TimeoutException:
        return UpdateResult(
            available=False,
            current_version=current,
            error="Update check timed out",
        )
    except Exception as exc:
        log.warning("Update check failed: %s", exc)
        return UpdateResult(
            available=False,
            current_version=current,
            error=str(exc),
        )


def check_for_updates_async(
    callback: Callable[[UpdateResult], None],
) -> threading.Thread:
    """Check for updates in background thread, call callback with result."""
    def worker():
        result = check_for_updates()
        callback(result)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


class Updater:
    """Handles downloading and applying updates."""

    def __init__(self, release_info: ReleaseInfo):
        self.release_info = release_info
        self._progress_callback: Optional[Callable[[int, int], None]] = None
        self._cancelled = False

    def set_progress_callback(self, callback: Callable[[int, int], None]) -> None:
        self._progress_callback = callback

    def cancel(self) -> None:
        self._cancelled = True

    def download_and_apply(self) -> tuple[bool, str]:
        """Download and apply the update. Returns (success, message)."""
        try:
            if is_msi_installation():
                return self._apply_msi_update()
            else:
                return self._apply_zip_update()
        except Exception as exc:
            log.exception("Update failed: %s", exc)
            return False, str(exc)

    def _apply_msi_update(self) -> tuple[bool, str]:
        """Download and run MSI installer."""
        if not self.release_info.msi_url:
            return False, "No MSI installer available for this release"

        temp_dir = Path(tempfile.mkdtemp(prefix="openwhisper_update_"))
        msi_path = temp_dir / f"OpenWhisper-{self.release_info.version}.msi"

        try:
            success, msg = self._download_file(self.release_info.msi_url, msi_path)
            if not success:
                return False, msg

            log.info("Running MSI installer: %s", msi_path)
            subprocess.Popen(
                ["msiexec", "/i", str(msi_path), "/passive", "/norestart"],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            return True, "Update started. The application will restart."

        except Exception as exc:
            return False, f"MSI update failed: {exc}"

    def _apply_zip_update(self) -> tuple[bool, str]:
        """Download ZIP and prepare for update on next launch."""
        if not self.release_info.zip_url:
            return False, "No ZIP file available for this release"

        update_dir = app_data_dir() / "pending_update"
        update_dir.mkdir(parents=True, exist_ok=True)

        temp_zip = update_dir / "update.zip"
        extract_dir = update_dir / "extracted"

        try:
            if extract_dir.exists():
                shutil.rmtree(extract_dir)

            success, msg = self._download_file(self.release_info.zip_url, temp_zip)
            if not success:
                return False, msg

            log.info("Extracting update to: %s", extract_dir)
            with zipfile.ZipFile(temp_zip, "r") as zf:
                zf.extractall(extract_dir)

            temp_zip.unlink()

            marker = update_dir / "update_ready.txt"
            marker.write_text(self.release_info.version, encoding="utf-8")

            return True, "Update downloaded. Restart the application to apply."

        except Exception as exc:
            if update_dir.exists():
                shutil.rmtree(update_dir, ignore_errors=True)
            return False, f"ZIP update failed: {exc}"

    def _download_file(self, url: str, dest: Path) -> tuple[bool, str]:
        """Download file with progress reporting."""
        try:
            with httpx.Client(timeout=300.0, follow_redirects=True) as client:
                with client.stream("GET", url) as resp:
                    if resp.status_code != 200:
                        return False, f"Download failed: HTTP {resp.status_code}"

                    total = int(resp.headers.get("content-length", 0))
                    downloaded = 0

                    with open(dest, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=65536):
                            if self._cancelled:
                                return False, "Download cancelled"
                            f.write(chunk)
                            downloaded += len(chunk)
                            if self._progress_callback and total > 0:
                                self._progress_callback(downloaded, total)

            log.info("Downloaded %s to %s", url, dest)
            return True, "Download complete"

        except Exception as exc:
            return False, f"Download error: {exc}"


def apply_pending_update() -> bool:
    """Apply a pending ZIP update if one exists. Call at app startup."""
    update_dir = app_data_dir() / "pending_update"
    marker = update_dir / "update_ready.txt"

    if not marker.exists():
        return False

    extract_dir = update_dir / "extracted"
    if not extract_dir.exists():
        shutil.rmtree(update_dir, ignore_errors=True)
        return False

    try:
        exe_dir = get_exe_directory()
        log.info("Applying pending update from %s to %s", extract_dir, exe_dir)

        source_dirs = list(extract_dir.iterdir())
        if len(source_dirs) == 1 and source_dirs[0].is_dir():
            source_dir = source_dirs[0]
        else:
            source_dir = extract_dir

        backup_dir = app_data_dir() / "update_backup"
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)

        for item in source_dir.iterdir():
            dest = exe_dir / item.name
            if dest.exists():
                backup_dest = backup_dir / item.name
                backup_dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.is_dir():
                    shutil.copytree(dest, backup_dest)
                else:
                    shutil.copy2(dest, backup_dest)

            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        shutil.rmtree(update_dir, ignore_errors=True)
        shutil.rmtree(backup_dir, ignore_errors=True)

        log.info("Update applied successfully")
        return True

    except Exception as exc:
        log.exception("Failed to apply pending update: %s", exc)
        shutil.rmtree(update_dir, ignore_errors=True)
        return False
