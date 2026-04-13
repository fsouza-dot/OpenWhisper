"""Onboarding dialog. Lists the things the user needs to set up on first
launch. Unlike macOS, Windows doesn't gate the microphone behind a
system-level per-app grant the same way, but we still want to:
  1. Make sure the mic works (try to open a stream).
  2. Let the user paste their Groq key (optional, enables cloud STT).
  3. Tell them where the whisper model will be downloaded on first use.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ..keyring_store import SecretStore


class OnboardingDialog(QDialog):
    def __init__(self, secrets: SecretStore, on_done: Callable[[], None]):
        super().__init__()
        self.setWindowTitle("Welcome to OpenWhisper")
        self.setMinimumSize(520, 440)
        self._secrets = secrets
        self._on_done = on_done

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        title = QLabel("Welcome to OpenWhisper")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(title)

        layout.addWidget(
            self._wrap(
                "OpenWhisper runs whisper locally on your machine and polishes "
                "your text with local heuristics. Your audio never leaves "
                "this computer."
            )
        )

        layout.addWidget(self._section("1. Microphone"))
        layout.addWidget(
            self._wrap(
                "Make sure Windows has your microphone selected as the default "
                "recording device. The first time you press the hotkey, Windows "
                "may ask to let OpenWhisper use it."
            )
        )
        test_btn = QPushButton("Test microphone access")
        test_btn.clicked.connect(self._test_mic)
        layout.addWidget(test_btn)

        layout.addWidget(self._section("2. Whisper model"))
        layout.addWidget(
            self._wrap(
                "The first time you press the hotkey, faster-whisper will "
                "download the small.en model (~460 MB). You'll see it happen "
                "in the log; after that everything stays local and fast."
            )
        )

        layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self._finish)
        buttons.accepted.connect(self._finish)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(
            self._finish
        )
        layout.addWidget(buttons)

    def _section(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 14px; font-weight: 600; margin-top: 6px;")
        return label

    def _wrap(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        label.setStyleSheet("color: #aaa;")
        return label

    def _test_mic(self) -> None:
        try:
            import sounddevice as sd  # local import to keep startup fast
            with sd.InputStream(samplerate=16_000, channels=1, dtype="float32"):
                pass
            QMessageBox.information(
                self, "Microphone OK", "Your microphone is available to OpenWhisper."
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Microphone unavailable",
                f"Could not open a recording stream:\n\n{exc}",
            )

    def _finish(self) -> None:
        self._on_done()
        self.accept()
