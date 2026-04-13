"""System tray icon. Exposes Settings / Onboarding / Quit, and reflects
the current phase via icon color."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QSize
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .ui_state import Phase, UIState


_PHASE_COLORS: dict[Phase, QColor] = {
    Phase.idle: QColor("#cccccc"),
    Phase.recording: QColor("#e74c3c"),
    Phase.transcribing: QColor("#3498db"),
    Phase.cleaning: QColor("#9b59b6"),
    Phase.inserting: QColor("#2ecc71"),
    Phase.error: QColor("#e67e22"),
}


def _make_dot_icon(color: QColor, size: int = 32) -> QIcon:
    """Draw a simple filled circle as the tray icon. Keeps us from
    shipping a binary asset for now."""
    pix = QPixmap(QSize(size, size))
    pix.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(color)
    painter.setPen(QColor(0, 0, 0, 0))
    margin = 4
    painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)
    painter.end()
    return QIcon(pix)


class TrayIcon(QSystemTrayIcon):
    def __init__(
        self,
        state: UIState,
        on_open_settings: Callable[[], None],
        on_open_onboarding: Callable[[], None],
        on_quit: Callable[[], None],
    ):
        super().__init__(_make_dot_icon(_PHASE_COLORS[Phase.idle]))
        self.state = state
        self.setToolTip("OpenWhisper")

        menu = QMenu()
        title = QAction("OpenWhisper", menu)
        title.setEnabled(False)
        menu.addAction(title)
        menu.addSeparator()

        settings_action = QAction("Settings…", menu)
        settings_action.triggered.connect(on_open_settings)
        menu.addAction(settings_action)

        onboarding_action = QAction("Onboarding / Setup…", menu)
        onboarding_action.triggered.connect(on_open_onboarding)
        menu.addAction(onboarding_action)

        menu.addSeparator()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(on_quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        state.phaseChanged.connect(self._on_phase)

    def _on_phase(self, phase: Phase, _message: str) -> None:
        color = _PHASE_COLORS.get(phase, _PHASE_COLORS[Phase.idle])
        self.setIcon(_make_dot_icon(color))
        self.setToolTip(f"OpenWhisper — {self.state.phase_title()}")
