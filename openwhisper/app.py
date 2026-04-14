"""Application composition root.

Owns every long-lived service and the Qt application. Wires the
coordinator to the UI, the hotkey to the coordinator, and the settings
to everything.
"""
from __future__ import annotations

import signal
import sys
import threading
from typing import Optional

from PySide6.QtCore import QLockFile, QObject
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from .audio.recorder import AudioRecorder
from .cleanup.pipeline import CleanupPipeline
from .config import app_data_dir, asset_path
from .coordinator import DictationCoordinator
from .history import DictationHistory
from .hotkey.hotkey_manager import HotkeyManager
from .platform import get_platform
from .keyring_store import SecretStore
from .logging_setup import get_logger, setup_logging
from .protocols import SpeechToTextProvider
from .settings import AppSettings, SettingsStore, STTProviderKind
from .stt.groq_provider import GroqWhisperProvider
from .stt.whisper_provider import FasterWhisperProvider
from .usage import UsageTracker
from .ui.hud import HUDWindow
from .ui.onboarding import OnboardingDialog
from .ui.settings_window import SettingsWindow
from .ui.tray import TrayIcon
from .ui.ui_state import Phase, UIState

log = get_logger("app")


class OpenWhisperApp(QObject):
    def __init__(self, qt_app: QApplication):
        super().__init__()
        self.qt_app = qt_app

        # ---- persistence + secrets
        self.settings_store = SettingsStore()
        self.secrets = SecretStore()
        self.usage = UsageTracker()

        # ---- services
        self.ui_state = UIState()
        self.history = DictationHistory(
            capacity=self.settings_store.settings.history_size
        )
        self.recorder = AudioRecorder()
        self.recorder.set_device(self.settings_store.settings.input_device)
        self.settings_store.subscribe(
            lambda s: self.recorder.set_device(s.input_device)
        )
        self.hotkey = HotkeyManager()
        self._platform = get_platform()
        self.inserter = self._platform.create_inserter(
            restore_clipboard=self.settings_store.settings.restore_clipboard
        )

        self._stt_instance: Optional[SpeechToTextProvider] = None
        self._build_dynamic_services(self.settings_store.settings)

        self.coordinator = DictationCoordinator(
            settings_store=self.settings_store,
            recorder=self.recorder,
            stt_factory=self._get_stt,
            cleanup_factory=self._get_cleanup,
            inserter=self.inserter,
            hotkey=self.hotkey,
            history=self.history,
            ui_state=self.ui_state,
        )

        # ---- UI
        self.hud = HUDWindow(self.ui_state)
        self.tray = TrayIcon(
            state=self.ui_state,
            on_open_settings=self.show_settings,
            on_open_onboarding=self.show_onboarding,
            on_quit=self.quit,
        )
        self.tray.show()
        self._settings_window: Optional[SettingsWindow] = None
        self._onboarding_window: Optional[OnboardingDialog] = None

        # ---- start
        self.coordinator.start()
        self.ui_state.set_phase(Phase.idle, "")

        log.info(
            "OpenWhisper is running. Hotkeys: %s",
            ", ".join(
                b.pynput_hotkey_string()
                for b in self.settings_store.settings.hotkeys
            ),
        )

        if not self.secrets.get_groq_key():
            # First-run: no key yet. Show onboarding.
            self.show_onboarding()

    # -------------------------------------------------- dynamic service build

    def _build_dynamic_services(self, settings: AppSettings) -> None:
        """Build STT + LLM providers from the current settings. Called on
        launch and whenever settings change."""
        # Pick STT backend. Groq is strongly preferred for latency when a
        # key is set; fall back to local whisper if Groq is unavailable.
        self._stt_instance = None
        if settings.stt_provider == STTProviderKind.groq:
            groq_key = self.secrets.get_groq_key()
            if groq_key:
                try:
                    self._stt_instance = GroqWhisperProvider(
                        api_key=groq_key,
                        model=settings.groq_model,
                        languages=settings.languages,
                        on_usage=self.usage.record_audio_seconds,
                    )
                    log.info("STT backend: Groq (%s)", settings.groq_model)
                except Exception as exc:
                    log.warning("Could not init Groq STT: %s — falling back to local", exc)
            else:
                log.warning("Groq selected but no API key — falling back to local whisper")

        if self._stt_instance is None:
            self._stt_instance = FasterWhisperProvider(
                model_size=settings.whisper_model_size,
                compute_type=settings.whisper_compute_type,
                languages=settings.languages,
            )
            log.info("STT backend: local faster-whisper (%s)", settings.whisper_model_size)
            # Warm the whisper model in the background so the first hotkey
            # press doesn't eat the model-load cost (~2-5s on CPU).
            stt = self._stt_instance
            if hasattr(stt, "warmup"):
                threading.Thread(target=stt.warmup, daemon=True).start()

    def _get_stt(self) -> SpeechToTextProvider:
        assert self._stt_instance is not None
        return self._stt_instance

    def _get_cleanup(self) -> CleanupPipeline:
        return CleanupPipeline(llm_provider=None)

    # ------------------------------------------------------- ui dialogs

    def show_settings(self) -> None:
        dlg = SettingsWindow(
            store=self.settings_store,
            secrets=self.secrets,
            usage=self.usage,
            on_save=self._on_settings_saved,
        )
        dlg.exec()

    def show_onboarding(self) -> None:
        dlg = OnboardingDialog(
            secrets=self.secrets,
            on_done=self._on_settings_saved,
        )
        dlg.exec()

    def _on_settings_saved(self) -> None:
        log.info("Settings updated — rebuilding services")
        self._build_dynamic_services(self.settings_store.settings)
        self.inserter.restore_clipboard = self.settings_store.settings.restore_clipboard
        self.history.capacity = self.settings_store.settings.history_size
        self.coordinator.reload_hotkey()

    # ------------------------------------------------------- quit

    def quit(self) -> None:
        log.info("Shutting down OpenWhisper")
        try:
            self.coordinator.stop()
        except Exception:  # pragma: no cover
            pass
        self.qt_app.quit()


def run() -> int:
    setup_logging()
    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)
    icon_file = asset_path("icon.ico")
    if icon_file.exists():
        qt_app.setWindowIcon(QIcon(str(icon_file)))

    # Single-instance guard. Stale locks from a crashed prior run are
    # cleaned up automatically after 5s (QLockFile checks the PID).
    lock_path = str(app_data_dir() / "openwhisper.lock")
    lock = QLockFile(lock_path)
    lock.setStaleLockTime(5000)
    if not lock.tryLock(100):
        log.warning("Another OpenWhisper instance is already running — exiting.")
        QMessageBox.information(
            None,
            "OpenWhisper already running",
            "OpenWhisper is already running. Check the system tray.",
        )
        return 0

    # Route Ctrl+C to a clean shutdown when run from a terminal.
    signal.signal(signal.SIGINT, lambda *_: qt_app.quit())

    app = OpenWhisperApp(qt_app)
    try:
        return qt_app.exec()
    finally:
        app.quit()
        lock.unlock()
