"""Minimal floating HUD - black background with white audio waveform lines."""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .ui_state import Phase, UIState


class HUDWindow(QWidget):
    """Simple HUD with animated audio waveform lines."""

    NUM_BARS = 5        # Number of vertical bars
    BAR_WIDTH = 3       # Width of each bar
    BAR_GAP = 4         # Gap between bars
    MAX_BAR_HEIGHT = 20 # Maximum bar height

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

        # Calculate size based on bars
        total_width = self.NUM_BARS * self.BAR_WIDTH + (self.NUM_BARS - 1) * self.BAR_GAP + 24
        self.setFixedSize(total_width, 36)

        self._phase = Phase.idle
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

        # Black background with rounded corners
        p.setBrush(QColor(0, 0, 0, 230))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 8, 8)

        # Draw centered white waveform bars
        cx = self.width() // 2
        cy = self.height() // 2

        # Calculate total width of all bars
        total_bars_width = self.NUM_BARS * self.BAR_WIDTH + (self.NUM_BARS - 1) * self.BAR_GAP
        start_x = cx - total_bars_width // 2

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255))

        for i in range(self.NUM_BARS):
            # Animate each bar with different phase offset
            phase_offset = i * 0.7
            height = 4 + abs(math.sin(self._time / 120 + phase_offset)) * (self.MAX_BAR_HEIGHT - 4)

            x = start_x + i * (self.BAR_WIDTH + self.BAR_GAP)
            y = cy - height / 2

            p.drawRoundedRect(int(x), int(y), self.BAR_WIDTH, int(height), 1, 1)

    def showEvent(self, e) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen:
            g = screen.availableGeometry()
            self.move(g.center().x() - self.width() // 2, g.bottom() - self.height() - 80)
        super().showEvent(e)

    def _on_phase(self, phase: Phase, _msg: str) -> None:
        self._phase = phase

        if phase == Phase.idle:
            self._timer.stop()
            self._hide_timer.start(50)  # Hide almost immediately
        else:
            self._hide_timer.stop()
            self._time = 0
            self._timer.start()
            self.show()
            self.raise_()
