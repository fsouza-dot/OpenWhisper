"""Minimal floating HUD - small, elegant pill overlay."""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from .ui_state import Phase, UIState


_PHASE_COLORS: dict[Phase, QColor] = {
    Phase.idle: QColor(100, 100, 105),
    Phase.recording: QColor(255, 59, 48),      # Red
    Phase.transcribing: QColor(50, 173, 230),  # Blue
    Phase.cleaning: QColor(175, 130, 255),     # Purple
    Phase.inserting: QColor(48, 209, 88),      # Green
    Phase.error: QColor(255, 149, 0),          # Orange
}


class HUDWindow(QWidget):
    """Tiny pill HUD with animated dots."""

    def __init__(self, state: UIState):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.state = state
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Small and compact
        self.setFixedSize(64, 28)

        self._phase = Phase.idle
        self._color = _PHASE_COLORS[Phase.idle]
        self._time = 0

        # Animation
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.setInterval(50)

        # Auto-hide
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        state.phaseChanged.connect(self._on_phase)

    def _tick(self) -> None:
        self._time += 50
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background pill
        bg = QPainterPath()
        r = self.rect().adjusted(1, 1, -1, -1)
        bg.addRoundedRect(r, r.height() / 2, r.height() / 2)
        p.fillPath(bg, QColor(28, 28, 30, 240))

        # Draw 3 animated dots for recording, single dot otherwise
        cx, cy = r.center().x(), r.center().y()

        if self._phase == Phase.recording:
            # 3 bouncing dots
            for i in range(3):
                offset = math.sin(self._time / 150 + i * 0.8) * 4
                x = cx - 12 + i * 12
                y = cy + offset
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(self._color)
                p.drawEllipse(int(x) - 3, int(y) - 3, 6, 6)
        else:
            # Single pulsing dot
            if self._phase in (Phase.transcribing, Phase.cleaning):
                alpha = int(180 + 75 * math.sin(self._time / 150))
                color = QColor(self._color.red(), self._color.green(), self._color.blue(), alpha)
            else:
                color = self._color
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawEllipse(int(cx) - 4, int(cy) - 4, 8, 8)

    def showEvent(self, e) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen:
            g = screen.availableGeometry()
            self.move(g.center().x() - self.width() // 2, g.bottom() - self.height() - 80)
        super().showEvent(e)

    def _on_phase(self, phase: Phase, _msg: str) -> None:
        self._phase = phase
        self._color = _PHASE_COLORS.get(phase, _PHASE_COLORS[Phase.idle])

        if phase == Phase.idle:
            self._timer.stop()
            self._hide_timer.start(400)
        else:
            self._hide_timer.stop()
            self._time = 0
            self._timer.start()
            self.show()
            self.raise_()
