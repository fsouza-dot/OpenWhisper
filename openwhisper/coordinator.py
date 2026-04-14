"""The dictation state machine. Owns the flow:

    idle → recording → transcribing → cleaning → inserting → idle

All expensive work (STT + LLM cleanup) runs on a background thread so
the Qt event loop stays responsive and hotkey callbacks are never
blocked. UIState updates are marshalled back to the Qt thread via
queued signals.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from .cleanup.pipeline import CleanupPipeline
from .commands.command import DictationCommand
from .errors import OpenWhisperError
from .history import DictationHistory, HistoryEntry
from .hotkey.hotkey_manager import HotkeyEvent, HotkeyManager
from .insertion.paste_inserter import PasteboardInserter
from .logging_setup import get_logger
from .protocols import AudioBuffer, SpeechToTextProvider, TextInsertionProvider
from .audio.recorder import AudioRecorder
from .cleanup.dictionary import PersonalDictionary
from .settings import AppSettings, HotkeyMode, SettingsStore
from .ui.ui_state import Phase, UIState

log = get_logger("coordinator")


class DictationCoordinator(QObject):
    # Internal signal so background threads can publish back to the Qt thread.
    _phase_signal = Signal(Phase, str)
    _preview_signal = Signal(str)
    _inserted_signal = Signal(str)
    _schedule_idle_signal = Signal(int)

    def __init__(
        self,
        settings_store: SettingsStore,
        recorder: AudioRecorder,
        stt_factory: Callable[[], SpeechToTextProvider],
        cleanup_factory: Callable[[], CleanupPipeline],
        inserter: TextInsertionProvider,
        hotkey: HotkeyManager,
        history: DictationHistory,
        ui_state: UIState,
    ):
        super().__init__()
        self._settings_store = settings_store
        self._recorder = recorder
        self._stt_factory = stt_factory
        self._cleanup_factory = cleanup_factory
        self._inserter = inserter
        self._hotkey = hotkey
        self._history = history
        self._ui_state = ui_state

        self._is_recording = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Connect internal signals to UI state on the Qt thread.
        self._phase_signal.connect(self._on_phase_signal)
        self._preview_signal.connect(self._ui_state.set_live_preview)
        self._inserted_signal.connect(self._ui_state.set_last_inserted)
        self._schedule_idle_signal.connect(self._on_schedule_idle)

    # ---------------------------------------------------------- lifecycle

    def start(self) -> None:
        self.reload_hotkey()
        self._hotkey.on_event = self._handle_hotkey

    def stop(self) -> None:
        self._hotkey.unregister()
        if self._is_recording:
            try:
                self._recorder.stop()
            except Exception:  # pragma: no cover
                pass

    def reload_hotkey(self) -> None:
        self._hotkey.register(self._settings_store.settings.hotkeys)

    # --------------------------------------------------------- hotkey flow

    def _handle_hotkey(self, event: str) -> None:
        mode = self._settings_store.settings.hotkey_mode
        with self._lock:
            if mode == HotkeyMode.push_to_talk:
                if event == HotkeyEvent.PRESSED and not self._is_recording:
                    self._begin_recording()
                elif event == HotkeyEvent.RELEASED and self._is_recording:
                    self._end_recording()
            elif mode == HotkeyMode.toggle:
                if event == HotkeyEvent.PRESSED:
                    if self._is_recording:
                        self._end_recording()
                    else:
                        self._begin_recording()

    def _begin_recording(self) -> None:
        try:
            self._recorder.start()
        except OpenWhisperError as exc:
            log.error("Could not start recording: %s", exc)
            self._phase_signal.emit(Phase.error, str(exc))
            self._schedule_idle(1200)
            return
        self._is_recording = True
        self._phase_signal.emit(Phase.recording, "")
        self._preview_signal.emit("")

    def _end_recording(self) -> None:
        audio = self._recorder.stop()
        self._is_recording = False
        self._phase_signal.emit(Phase.transcribing, "")
        # Kick the heavy work onto a worker thread so the UI stays responsive.
        self._worker_thread = threading.Thread(
            target=self._run_pipeline,
            args=(audio,),
            daemon=True,
        )
        self._worker_thread.start()

    # ------------------------------------------------------ worker pipeline

    def _run_pipeline(self, audio: AudioBuffer) -> None:
        settings = self._settings_store.settings
        t0 = time.time()

        if audio.samples.size == 0:
            self._phase_signal.emit(Phase.idle, "")
            return

        # 1. STT
        try:
            stt = self._stt_factory()
            hints = PersonalDictionary(settings.dictionary).stt_hints()
            transcript = stt.transcribe(audio, hints)
        except OpenWhisperError as exc:
            log.error("Transcription failed: %s", exc)
            self._phase_signal.emit(Phase.error, "Transcription failed")
            self._schedule_idle(1500)
            return
        except Exception as exc:
            log.exception("Unexpected transcription error: %s", exc)
            self._phase_signal.emit(Phase.error, "Transcription failed")
            self._schedule_idle(1500)
            return

        if not transcript.text.strip():
            self._phase_signal.emit(Phase.idle, "")
            return

        self._preview_signal.emit(transcript.text)
        self._phase_signal.emit(Phase.cleaning, "")

        # 2. Cleanup
        try:
            pipeline = self._cleanup_factory()
            result = pipeline.run(transcript.text, settings)
        except Exception as exc:
            log.exception("Cleanup failed: %s", exc)
            self._phase_signal.emit(Phase.error, "Cleanup failed")
            self._schedule_idle(1500)
            return

        # 3. Commands
        command: Optional[DictationCommand] = None
        if result.command:
            try:
                command = DictationCommand(result.command)
            except ValueError:
                log.warning("Unknown command in result: %s", result.command)

        if command is not None:
            self._execute_command(command, settings)

        # 4. Insertion
        if result.cleaned:
            self._phase_signal.emit(Phase.inserting, "")
            try:
                self._inserter.insert(result.cleaned)
                self._inserted_signal.emit(result.cleaned)
                self._history.record(
                    HistoryEntry(
                        raw_transcript=transcript.text,
                        final_text=result.cleaned,
                        inserted_into=_frontmost_app_name(),
                    )
                )
            except Exception as exc:
                log.exception("Insertion failed: %s", exc)
                self._phase_signal.emit(Phase.error, "Paste failed")
                self._schedule_idle(1500)
                return

        log.info("Pipeline complete in %.2fs (used_llm=%s, model=%s)",
                 time.time() - t0, result.used_llm, result.model_used)
        self._phase_signal.emit(Phase.idle, "")  # Hide immediately

    # ------------------------------------------------------------ commands

    def _execute_command(self, cmd: DictationCommand, settings: AppSettings) -> None:
        log.info("Executing command: %s", cmd.value)
        if cmd.is_destructive and settings.confirm_destructive_commands:
            # MVP policy: for destructive commands we log and skip rather
            # than popping a modal that would steal focus from the
            # user's target app. A future version can add a HUD-based
            # confirm button.
            log.warning("Skipping destructive command %s (confirmations enabled)", cmd.value)
            return

        paster = self._inserter
        if not isinstance(paster, PasteboardInserter):
            return

        try:
            if cmd == DictationCommand.new_line:
                paster.insert("\n")
            elif cmd == DictationCommand.new_paragraph:
                paster.insert("\n\n")
            elif cmd == DictationCommand.bullet_list:
                paster.insert("\n- ")
            elif cmd == DictationCommand.numbered_list:
                paster.insert("\n1. ")
            elif cmd == DictationCommand.press_enter or cmd == DictationCommand.send:
                paster.press_key("enter")
            elif cmd == DictationCommand.press_tab:
                paster.press_key("tab")
            elif cmd == DictationCommand.press_escape:
                paster.press_key("escape")
            elif cmd == DictationCommand.delete_last:
                paster.press_key("backspace")
            elif cmd == DictationCommand.undo_last_dictation:
                self._undo_last()
            # rewrite_* commands are reflected in `result.cleaned` already.
        except Exception as exc:
            log.warning("Command execution failed: %s", exc)

    def _undo_last(self) -> None:
        last = self._history.pop_last()
        if last is None:
            return
        paster = self._inserter
        if not isinstance(paster, PasteboardInserter):
            return
        # Best-effort: spam backspace equal to the inserted length.
        for _ in range(len(last.final_text)):
            try:
                paster.press_key("backspace")
            except Exception:  # pragma: no cover
                break

    # ------------------------------------------------------------- helpers

    @Slot(Phase, str)
    def _on_phase_signal(self, phase: Phase, message: str) -> None:
        self._ui_state.set_phase(phase, message)

    def _schedule_idle(self, delay_ms: int) -> None:
        # Safe to call from any thread: hops onto the Qt thread via signal
        # before touching QTimer (QTimer must be created on its owner thread).
        self._schedule_idle_signal.emit(delay_ms)

    @Slot(int)
    def _on_schedule_idle(self, delay_ms: int) -> None:
        QTimer.singleShot(delay_ms, lambda: self._ui_state.set_phase(Phase.idle, ""))


def _frontmost_app_name() -> Optional[str]:
    """Best-effort Windows foreground window lookup. Falls back to None
    on any error so the coordinator never breaks on a missing dep."""
    try:
        import ctypes  # type: ignore
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hwnd = user32.GetForegroundWindow()
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not handle:
            return None
        buf = ctypes.create_unicode_buffer(512)
        size = ctypes.c_ulong(len(buf))
        ok = kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
        kernel32.CloseHandle(handle)
        if not ok:
            return None
        return buf.value.split("\\")[-1]
    except Exception:
        return None
