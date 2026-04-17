"""Update notification and download dialog."""
from __future__ import annotations

import webbrowser
from typing import Optional

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import asset_path
from ..updater import ReleaseInfo, Updater


_DIALOG_STYLE = """
QDialog {
    background-color: #1f1f1f;
}
QLabel {
    color: #e4e4e4;
    background: transparent;
}
QLabel#title {
    font-size: 18px;
    font-weight: 600;
    color: #ffffff;
}
QLabel#subtitle {
    font-size: 13px;
    color: #9d9d9d;
}
QTextEdit {
    background-color: #2d2d2d;
    color: #e4e4e4;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    padding: 8px;
    font-size: 12px;
}
QPushButton {
    background-color: #0078d4;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 13px;
    min-width: 100px;
}
QPushButton:hover {
    background-color: #1a86d9;
}
QPushButton:pressed {
    background-color: #006cbd;
}
QPushButton#secondary {
    background-color: #3d3d3d;
    color: #e4e4e4;
}
QPushButton#secondary:hover {
    background-color: #4d4d4d;
}
QProgressBar {
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    background-color: #2d2d2d;
    text-align: center;
    color: #e4e4e4;
}
QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 3px;
}
"""


class DownloadThread(QThread):
    """Background thread for downloading updates."""
    progress = Signal(int, int)
    finished = Signal(bool, str)

    def __init__(self, updater: Updater):
        super().__init__()
        self._updater = updater
        self._updater.set_progress_callback(self._on_progress)

    def _on_progress(self, downloaded: int, total: int) -> None:
        self.progress.emit(downloaded, total)

    def run(self) -> None:
        success, message = self._updater.download_and_apply()
        self.finished.emit(success, message)

    def cancel(self) -> None:
        self._updater.cancel()


class UpdateAvailableDialog(QDialog):
    """Dialog shown when an update is available."""

    def __init__(
        self,
        current_version: str,
        release_info: ReleaseInfo,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._release_info = release_info
        self._updater: Optional[Updater] = None
        self._download_thread: Optional[DownloadThread] = None

        self.setWindowTitle("Update Available")
        self.setMinimumSize(500, 400)
        self.resize(550, 450)
        self.setStyleSheet(_DIALOG_STYLE)

        icon_file = asset_path("icon.ico")
        if icon_file.exists():
            self.setWindowIcon(QIcon(str(icon_file)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("A new version is available!")
        title.setObjectName("title")
        layout.addWidget(title)

        version_text = f"Current version: {current_version}  →  New version: {release_info.version}"
        subtitle = QLabel(version_text)
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        notes_label = QLabel("What's new:")
        layout.addWidget(notes_label)

        self._notes = QTextEdit()
        self._notes.setReadOnly(True)
        self._notes.setPlainText(release_info.release_notes or "No release notes available.")
        self._notes.setMinimumHeight(150)
        layout.addWidget(self._notes)

        self._progress_container = QWidget()
        progress_layout = QVBoxLayout(self._progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)

        self._progress_label = QLabel("Downloading update...")
        progress_layout.addWidget(self._progress_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        progress_layout.addWidget(self._progress_bar)

        self._progress_container.hide()
        layout.addWidget(self._progress_container)

        layout.addStretch(1)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self._view_btn = QPushButton("View on GitHub")
        self._view_btn.setObjectName("secondary")
        self._view_btn.clicked.connect(self._open_release_page)
        button_layout.addWidget(self._view_btn)

        button_layout.addStretch(1)

        self._later_btn = QPushButton("Later")
        self._later_btn.setObjectName("secondary")
        self._later_btn.clicked.connect(self.reject)
        button_layout.addWidget(self._later_btn)

        self._update_btn = QPushButton("Update Now")
        self._update_btn.clicked.connect(self._start_update)
        button_layout.addWidget(self._update_btn)

        layout.addLayout(button_layout)

    def _open_release_page(self) -> None:
        if self._release_info.release_url:
            webbrowser.open(self._release_info.release_url)

    def _start_update(self) -> None:
        self._update_btn.setEnabled(False)
        self._later_btn.setText("Cancel")
        self._later_btn.clicked.disconnect()
        self._later_btn.clicked.connect(self._cancel_update)
        self._view_btn.setEnabled(False)
        self._notes.hide()

        self._progress_container.show()
        self._progress_label.setText("Preparing download...")

        self._updater = Updater(self._release_info)
        self._download_thread = DownloadThread(self._updater)
        self._download_thread.progress.connect(self._on_progress)
        self._download_thread.finished.connect(self._on_finished)
        self._download_thread.start()

    def _cancel_update(self) -> None:
        if self._download_thread:
            self._download_thread.cancel()
        self.reject()

    def _on_progress(self, downloaded: int, total: int) -> None:
        percent = int((downloaded / total) * 100) if total > 0 else 0
        self._progress_bar.setValue(percent)
        mb_downloaded = downloaded / (1024 * 1024)
        mb_total = total / (1024 * 1024)
        self._progress_label.setText(
            f"Downloading... {mb_downloaded:.1f} MB / {mb_total:.1f} MB"
        )

    def _on_finished(self, success: bool, message: str) -> None:
        if success:
            self._progress_label.setText(message)
            self._progress_bar.setValue(100)
            self._later_btn.setText("Close")
            self._later_btn.clicked.disconnect()
            self._later_btn.clicked.connect(self.accept)
            self._update_btn.setText("Restart Now")
            self._update_btn.setEnabled(True)
            self._update_btn.clicked.disconnect()
            self._update_btn.clicked.connect(self._restart_app)
        else:
            self._progress_label.setText(f"Update failed: {message}")
            self._later_btn.setText("Close")
            self._later_btn.clicked.disconnect()
            self._later_btn.clicked.connect(self.reject)
            self._update_btn.setEnabled(False)

    def _restart_app(self) -> None:
        import sys
        import os
        os.execv(sys.executable, [sys.executable] + sys.argv)
