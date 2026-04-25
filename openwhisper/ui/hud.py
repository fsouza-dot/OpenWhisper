"""Minimal floating HUD - black background with white audio waveform lines."""
from __future__ import annotations

import math
import sys
from typing import List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter
from PySide6.QtWidgets import QWidget

from .ui_state import Phase, UIState


# Set to False to use fake sine-wave animation instead of real audio levels
USE_REAL_AUDIO_LEVELS = True


class HUDWindow(QWidget):
    """Simple HUD with audio waveform visualization.

    When USE_REAL_AUDIO_LEVELS is True, bars reflect actual microphone input.
    When False, uses a fake sine-wave animation (for rollback/testing).
    """

    NUM_BARS = 5        # Number of vertical bars
    BAR_WIDTH = 3       # Width of each bar
    BAR_GAP = 4         # Gap between bars
    MAX_BAR_HEIGHT = 22 # Maximum bar height
    MIN_BAR_HEIGHT = 2  # Minimum bar height

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

        # Real audio levels (0.0-1.0 for each bar)
        self._target_levels: List[float] = [0.0] * self.NUM_BARS
        self._display_levels: List[float] = [0.0] * self.NUM_BARS

        # Animation timer (for smooth interpolation and fallback animation)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.setInterval(30)  # ~33 FPS for smooth animation

        # Auto-hide
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        state.phaseChanged.connect(self._on_phase)

        if USE_REAL_AUDIO_LEVELS:
            state.audioLevelsChanged.connect(self._on_audio_levels)

    def _on_audio_levels(self, levels: List[float]) -> None:
        """Receive real audio levels from the microphone."""
        if len(levels) >= self.NUM_BARS:
            self._target_levels = levels[:self.NUM_BARS]

    def _tick(self) -> None:
        self._time += 30

        if USE_REAL_AUDIO_LEVELS and self._phase == Phase.recording:
            # Smooth interpolation toward target levels
            for i in range(self.NUM_BARS):
                target = self._target_levels[i]
                current = self._display_levels[i]
                # Fast rise, slower fall for natural feel
                if target > current:
                    self._display_levels[i] = current + (target - current) * 0.85
                else:
                    self._display_levels[i] = current + (target - current) * 0.6
        else:
            # Fake animation for non-recording phases or when disabled
            for i in range(self.NUM_BARS):
                phase_offset = i * 0.7
                self._display_levels[i] = abs(math.sin(self._time / 120 + phase_offset))

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
            level = self._display_levels[i]
            height = self.MIN_BAR_HEIGHT + level * (self.MAX_BAR_HEIGHT - self.MIN_BAR_HEIGHT)

            x = start_x + i * (self.BAR_WIDTH + self.BAR_GAP)
            y = cy - height / 2

            p.drawRoundedRect(int(x), int(y), self.BAR_WIDTH, int(height), 1, 1)

    def showEvent(self, e) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen:
            g = screen.availableGeometry()
            self.move(g.center().x() - self.width() // 2, g.bottom() - self.height() - 80)
        super().showEvent(e)
        if sys.platform == "darwin":
            from ..platform.macos import make_window_non_activating
            make_window_non_activating(self)

    def _on_phase(self, phase: Phase, _msg: str) -> None:
        self._phase = phase

        if phase == Phase.idle:
            self._timer.stop()
            # Reset levels
            self._target_levels = [0.0] * self.NUM_BARS
            self._display_levels = [0.0] * self.NUM_BARS
            self._hide_timer.start(50)  # Hide almost immediately
        else:
            self._hide_timer.stop()
            self._time = 0
            self._timer.start()
            self.show()
            # raise_() activates the app on macOS even with
            # WA_ShowWithoutActivating. We rely on NSWindow level=Floating
            # (set in make_window_non_activating) to keep the HUD above
            # other windows without touching focus.
            if sys.platform != "darwin":
                self.raise_()
