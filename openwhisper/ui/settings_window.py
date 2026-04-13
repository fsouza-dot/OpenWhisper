"""Settings dialog with five tabs: General, Hotkey, Dictionary, Snippets,
Advanced. Works on a draft copy of `AppSettings` so the user can cancel.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import sounddevice as sd
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..keyring_store import SecretStore
from ..usage import UsageTracker, UsageSnapshot
from ..settings import (
    AppSettings,
    CommandModeSetting,
    DictationMode,
    DictionaryEntry,
    HotkeyBinding,
    HotkeyMode,
    PasteBehavior,
    SettingsStore,
    Snippet,
    STTProviderKind,
)


# Qt.Key → pynput-style key name, for chord capture.
_QT_KEY_NAMES: dict[int, str] = {
    int(Qt.Key.Key_Space): "space",
    int(Qt.Key.Key_Tab): "tab",
    int(Qt.Key.Key_Return): "enter",
    int(Qt.Key.Key_Enter): "enter",
    int(Qt.Key.Key_Backspace): "backspace",
    int(Qt.Key.Key_Insert): "insert",
    int(Qt.Key.Key_Delete): "delete",
    int(Qt.Key.Key_Home): "home",
    int(Qt.Key.Key_End): "end",
    int(Qt.Key.Key_PageUp): "page_up",
    int(Qt.Key.Key_PageDown): "page_down",
    int(Qt.Key.Key_Left): "left",
    int(Qt.Key.Key_Right): "right",
    int(Qt.Key.Key_Up): "up",
    int(Qt.Key.Key_Down): "down",
    **{int(getattr(Qt.Key, f"Key_F{i}")): f"f{i}" for i in range(1, 13)},
}

_MODIFIER_ONLY_KEYS = {
    int(Qt.Key.Key_Control),
    int(Qt.Key.Key_Alt),
    int(Qt.Key.Key_AltGr),
    int(Qt.Key.Key_Shift),
    int(Qt.Key.Key_Meta),
}


def _qt_key_to_name(key: int) -> str | None:
    if key in _QT_KEY_NAMES:
        return _QT_KEY_NAMES[key]
    if int(Qt.Key.Key_A) <= key <= int(Qt.Key.Key_Z):
        return chr(ord("a") + (key - int(Qt.Key.Key_A)))
    if int(Qt.Key.Key_0) <= key <= int(Qt.Key.Key_9):
        return chr(ord("0") + (key - int(Qt.Key.Key_0)))
    return None


class HotkeyCaptureButton(QPushButton):
    """Click, then press a key combination — emits `captured` with the
    resulting HotkeyBinding. Escape cancels."""

    captured = Signal(object)  # HotkeyBinding

    _IDLE_LABEL = "Record new binding…"
    _CAPTURING_LABEL = "Press a key combination  (Esc to cancel)"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(self._IDLE_LABEL, parent)
        self._capturing = False
        self.setCheckable(True)
        self.clicked.connect(self._toggle_capture)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _toggle_capture(self) -> None:
        if self._capturing:
            self._end_capture(None)
        else:
            self._start_capture()

    def _start_capture(self) -> None:
        self._capturing = True
        self.setChecked(True)
        self.setText(self._CAPTURING_LABEL)
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.grabKeyboard()

    def _end_capture(self, binding: HotkeyBinding | None) -> None:
        self._capturing = False
        self.setChecked(False)
        self.setText(self._IDLE_LABEL)
        try:
            self.releaseKeyboard()
        except Exception:
            pass
        if binding is not None:
            self.captured.emit(binding)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if not self._capturing:
            return super().keyPressEvent(event)
        key = event.key()
        if key in _MODIFIER_ONLY_KEYS:
            event.accept()
            return
        if key == int(Qt.Key.Key_Escape):
            self._end_capture(None)
            event.accept()
            return
        mods_flags = event.modifiers()
        modifiers: list[str] = []
        if mods_flags & Qt.KeyboardModifier.ControlModifier:
            modifiers.append("ctrl")
        if mods_flags & Qt.KeyboardModifier.AltModifier:
            modifiers.append("alt")
        if mods_flags & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append("shift")
        if mods_flags & Qt.KeyboardModifier.MetaModifier:
            modifiers.append("cmd")
        name = _qt_key_to_name(key)
        if not name:
            event.accept()
            return
        self._end_capture(HotkeyBinding(key=name, modifiers=modifiers))
        event.accept()

    def focusOutEvent(self, event) -> None:  # noqa: N802
        if self._capturing:
            self._end_capture(None)
        super().focusOutEvent(event)


_COMPACT_QSS = """
QLineEdit, QComboBox, QSpinBox {
    padding: 4px 8px;
    min-height: 26px;
}
QPushButton {
    padding: 5px 14px;
    min-height: 26px;
}
QCheckBox { spacing: 6px; min-height: 22px; }
QTabBar::tab {
    padding: 6px 14px;
    min-height: 22px;
}
"""


def _tighten_form(form: QFormLayout) -> None:
    """Shared spacing for every form layout in the dialog."""
    form.setContentsMargins(12, 12, 12, 12)
    form.setHorizontalSpacing(14)
    form.setVerticalSpacing(10)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)


class SettingsWindow(QDialog):
    def __init__(
        self,
        store: SettingsStore,
        secrets: SecretStore,
        usage: UsageTracker,
        on_save: Callable[[], None],
    ):
        super().__init__()
        self.setWindowTitle("OpenWhisper Settings")
        self.setMinimumSize(640, 520)
        self.resize(720, 560)
        self.setStyleSheet(_COMPACT_QSS)
        self._store = store
        self._secrets = secrets
        self._usage = usage
        self._on_save = on_save
        self._draft: AppSettings = store.settings.model_copy(deep=True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        tabs = QTabWidget(self)
        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_microphone_tab(), "Microphone")
        tabs.addTab(self._build_hotkey_tab(), "Hotkey")
        tabs.addTab(self._build_dictionary_tab(), "Dictionary")
        tabs.addTab(self._build_snippets_tab(), "Snippets")
        tabs.addTab(self._build_advanced_tab(), "Advanced")
        layout.addWidget(tabs, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ============================================================= General

    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        _tighten_form(form)

        self._mode_combo = QComboBox()
        for m in DictationMode:
            self._mode_combo.addItem(m.value.capitalize(), m)
        self._mode_combo.setCurrentIndex(
            list(DictationMode).index(self._draft.dictation_mode)
        )
        form.addRow("Dictation mode", self._mode_combo)

        # Language checkboxes. Exactly one language = forced; multiple =
        # auto-detect per utterance.
        self._lang_en = QCheckBox("English")
        self._lang_pt = QCheckBox("Portuguese (Brazil)")
        self._lang_en.setChecked("en" in self._draft.languages)
        self._lang_pt.setChecked("pt" in self._draft.languages)
        lang_row = QHBoxLayout()
        lang_row.addWidget(self._lang_en)
        lang_row.addWidget(self._lang_pt)
        lang_row.addStretch(1)
        lang_row_w = QWidget()
        lang_row_w.setLayout(lang_row)
        form.addRow("Languages", lang_row_w)
        form.addRow(
            "",
            self._caption(
                "Enable multiple to auto-detect per utterance. Enabling any"
                " non-English language auto-switches to the multilingual"
                " whisper model."
            ),
        )

        self._stt_combo = QComboBox()
        _STT_LABELS = {
            STTProviderKind.whisper: "Local faster-whisper",
            STTProviderKind.groq: "Groq whisper-large-v3-turbo (cloud, fastest)",
        }
        for s in STTProviderKind:
            self._stt_combo.addItem(_STT_LABELS.get(s, s.value), s)
        self._stt_combo.setCurrentIndex(
            list(STTProviderKind).index(self._draft.stt_provider)
        )
        form.addRow("Speech-to-text backend", self._stt_combo)
        form.addRow(
            "",
            self._caption(
                "Groq runs whisper-large-v3-turbo on dedicated GPUs and"
                " finalizes a 5s clip in well under a second. Local"
                " faster-whisper is offline but slower."
            ),
        )

        self._groq_key_field = QLineEdit(self._secrets.get_groq_key())
        self._groq_key_field.setEchoMode(QLineEdit.EchoMode.Password)
        self._groq_key_field.setPlaceholderText("gsk_...")
        form.addRow("Groq API Key", self._groq_key_field)
        form.addRow(
            "",
            self._caption(
                "Get a free key at console.groq.com. Stored in Windows"
                " Credential Manager."
            ),
        )

        # ---- Groq free-tier usage bar
        self._usage_bar = QProgressBar()
        self._usage_bar.setRange(0, 1000)
        self._usage_bar.setTextVisible(True)
        self._usage_bar.setFixedHeight(18)
        form.addRow("Groq free tier (today)", self._usage_bar)
        self._usage_caption = self._caption("")
        form.addRow("", self._usage_caption)
        self._refresh_usage_bar()
        # Keep the bar live while the dialog is open.
        self._usage_timer = QTimer(self)
        self._usage_timer.setInterval(2000)
        self._usage_timer.timeout.connect(self._refresh_usage_bar)
        self._usage_timer.start()

        self._whisper_size = QComboBox()
        for size in ["tiny.en", "base.en", "small.en", "medium.en"]:
            self._whisper_size.addItem(size)
        self._whisper_size.setCurrentText(self._draft.whisper_model_size)
        form.addRow("Whisper model", self._whisper_size)

        self._whisper_compute = QComboBox()
        for ct in ["int8", "int8_float16", "float16", "float32"]:
            self._whisper_compute.addItem(ct)
        self._whisper_compute.setCurrentText(self._draft.whisper_compute_type)
        form.addRow("Whisper compute type", self._whisper_compute)
        form.addRow(
            "",
            self._caption(
                "int8 is fastest on CPU. Use float16 with CUDA for best speed + quality."
            ),
        )

        return w

    # ========================================================= Microphone

    def _build_microphone_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        form = QFormLayout()
        _tighten_form(form)
        form.setContentsMargins(0, 0, 0, 0)

        self._mic_combo = QComboBox()
        self._populate_mic_devices()
        form.addRow("Input device", self._mic_combo)

        refresh_btn = QPushButton("Refresh device list")
        refresh_btn.clicked.connect(self._populate_mic_devices)
        form.addRow("", refresh_btn)

        layout.addLayout(form)
        layout.addWidget(
            self._caption(
                "Pick the microphone OpenWhisper should record from. 'System default'"
                " follows whichever input Windows is currently using."
            )
        )

        # ---- test recording row
        self._mic_test_btn = QPushButton("Test mic (record 3s + play back)")
        self._mic_test_btn.clicked.connect(self._test_microphone)
        layout.addWidget(self._mic_test_btn)

        self._mic_test_status = QLabel("")
        self._mic_test_status.setWordWrap(True)
        layout.addWidget(self._mic_test_status)

        layout.addStretch(1)

        # state for the running test
        self._test_recording: np.ndarray | None = None
        self._test_stream: sd.InputStream | None = None
        self._test_chunks: list[np.ndarray] = []
        return w

    def _populate_mic_devices(self) -> None:
        self._mic_combo.blockSignals(True)
        self._mic_combo.clear()
        self._mic_combo.addItem("System default", None)
        try:
            devices = sd.query_devices()
        except Exception as exc:
            self._mic_combo.addItem(f"<error: {exc}>", None)
            self._mic_combo.blockSignals(False)
            return
        for dev in devices:
            if dev.get("max_input_channels", 0) > 0:
                name = dev.get("name", "?")
                self._mic_combo.addItem(name, name)
        # restore current selection
        current = self._draft.input_device
        if current:
            idx = self._mic_combo.findData(current)
            if idx >= 0:
                self._mic_combo.setCurrentIndex(idx)
        self._mic_combo.blockSignals(False)

    def _test_microphone(self) -> None:
        if self._test_stream is not None:
            return  # already running
        device_name = self._mic_combo.currentData()
        device_index = None
        if device_name:
            try:
                for idx, dev in enumerate(sd.query_devices()):
                    if dev.get("max_input_channels", 0) > 0 and dev.get("name") == device_name:
                        device_index = idx
                        break
            except Exception as exc:
                QMessageBox.critical(self, "Mic test failed", f"Could not query devices: {exc}")
                return

        sample_rate = 16_000
        self._test_chunks = []

        def callback(indata, frames, time_info, status):  # noqa: ARG001
            chunk = indata[:, 0].copy() if indata.ndim == 2 else indata.copy()
            self._test_chunks.append(chunk)

        try:
            self._test_stream = sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
                blocksize=1024,
                callback=callback,
                device=device_index,
            )
            self._test_stream.start()
        except Exception as exc:
            self._test_stream = None
            QMessageBox.critical(self, "Mic test failed", f"Could not open microphone:\n{exc}")
            return

        self._mic_test_btn.setEnabled(False)
        self._mic_test_status.setText("Recording 3 seconds — speak now…")
        QTimer.singleShot(3000, lambda: self._finish_mic_test(sample_rate))

    def _finish_mic_test(self, sample_rate: int) -> None:
        stream = self._test_stream
        self._test_stream = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

        if not self._test_chunks:
            self._mic_test_status.setText("No audio captured. Check that the mic is connected and not muted.")
            self._mic_test_btn.setEnabled(True)
            return

        samples = np.concatenate(self._test_chunks).astype(np.float32, copy=False).flatten()
        self._test_chunks = []
        peak = float(np.max(np.abs(samples))) if samples.size else 0.0
        rms = float(np.sqrt(np.mean(samples ** 2))) if samples.size else 0.0

        self._mic_test_status.setText(
            f"Captured {len(samples) / sample_rate:.1f}s — peak {peak:.3f}, "
            f"RMS {rms:.4f}. Playing back…"
        )

        try:
            sd.play(samples, samplerate=sample_rate)
        except Exception as exc:
            self._mic_test_status.setText(f"Recorded OK but playback failed: {exc}")
            self._mic_test_btn.setEnabled(True)
            return

        # Re-enable button after playback finishes (rough estimate).
        playback_ms = int((len(samples) / sample_rate) * 1000) + 250
        QTimer.singleShot(playback_ms, lambda: (
            self._mic_test_btn.setEnabled(True),
            self._mic_test_status.setText(
                self._mic_test_status.text().replace("Playing back…", "Done.")
                + ("  (silent — input level was 0)" if peak == 0 else "")
            ),
        ))

    # ============================================================= Hotkey

    def _build_hotkey_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        form = QFormLayout()
        _tighten_form(form)
        form.setContentsMargins(0, 0, 0, 0)

        self._hotkey_mode = QComboBox()
        for hm in HotkeyMode:
            self._hotkey_mode.addItem(hm.value.replace("_", " ").title(), hm)
        self._hotkey_mode.setCurrentIndex(
            list(HotkeyMode).index(self._draft.hotkey_mode)
        )
        form.addRow("Mode", self._hotkey_mode)

        self._command_mode = QComboBox()
        for cm in CommandModeSetting:
            self._command_mode.addItem(cm.value.replace("_", " ").title(), cm)
        self._command_mode.setCurrentIndex(
            list(CommandModeSetting).index(self._draft.command_mode)
        )
        form.addRow("Command mode", self._command_mode)
        layout.addLayout(form)

        layout.addWidget(QLabel("Bindings"))
        layout.addWidget(
            self._caption(
                "Any of these chords starts a dictation. Add as many as you"
                " like — push-to-talk tracks all of them simultaneously."
            )
        )

        self._bindings_list = QListWidget()
        self._bindings_list.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
        )
        for binding in self._draft.hotkeys:
            self._append_binding_item(binding)
        layout.addWidget(self._bindings_list, 1)

        row = QHBoxLayout()
        self._capture_btn = HotkeyCaptureButton()
        self._capture_btn.captured.connect(self._on_binding_captured)
        row.addWidget(self._capture_btn, 1)

        remove_btn = QPushButton("Remove selected")
        remove_btn.clicked.connect(self._remove_selected_binding)
        row.addWidget(remove_btn)
        layout.addLayout(row)

        self._confirm_destructive = QCheckBox(
            "Confirm destructive commands (send / delete / undo)"
        )
        self._confirm_destructive.setChecked(self._draft.confirm_destructive_commands)
        layout.addWidget(self._confirm_destructive)

        return w

    def _append_binding_item(self, binding: HotkeyBinding) -> None:
        item = QListWidgetItem(binding.display())
        item.setData(Qt.ItemDataRole.UserRole, binding.model_dump())
        self._bindings_list.addItem(item)

    def _on_binding_captured(self, binding: HotkeyBinding) -> None:
        # Reject duplicates.
        payload = binding.model_dump()
        for i in range(self._bindings_list.count()):
            if self._bindings_list.item(i).data(Qt.ItemDataRole.UserRole) == payload:
                return
        self._append_binding_item(binding)

    def _remove_selected_binding(self) -> None:
        row = self._bindings_list.currentRow()
        if row >= 0:
            self._bindings_list.takeItem(row)

    # ========================================================= Dictionary

    def _build_dictionary_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(QLabel("Personal dictionary"))
        layout.addWidget(
            self._caption(
                "Names, jargon, product terms. Aliases are what whisper may output;"
                " the term is how it should appear."
            )
        )

        input_row = QHBoxLayout()
        self._dict_term = QLineEdit()
        self._dict_term.setPlaceholderText("Term")
        self._dict_aliases = QLineEdit()
        self._dict_aliases.setPlaceholderText("Aliases (comma separated)")
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_dict_entry)
        input_row.addWidget(self._dict_term, 1)
        input_row.addWidget(self._dict_aliases, 2)
        input_row.addWidget(add_btn)
        layout.addLayout(input_row)

        self._dict_list = QListWidget()
        self._dict_list.itemDoubleClicked.connect(self._remove_selected_dict)
        for entry in self._draft.dictionary:
            self._append_dict_item(entry)
        layout.addWidget(self._dict_list, 1)
        layout.addWidget(self._caption("Double-click an entry to remove it."))
        return w

    def _append_dict_item(self, entry: DictionaryEntry) -> None:
        label = entry.term
        if entry.aliases:
            label += f"  —  aliases: {', '.join(entry.aliases)}"
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, entry.id)
        self._dict_list.addItem(item)

    def _add_dict_entry(self) -> None:
        term = self._dict_term.text().strip()
        if not term:
            return
        aliases = [a.strip() for a in self._dict_aliases.text().split(",") if a.strip()]
        entry = DictionaryEntry(term=term, aliases=aliases)
        self._draft.dictionary.append(entry)
        self._append_dict_item(entry)
        self._dict_term.clear()
        self._dict_aliases.clear()

    def _remove_selected_dict(self, item: QListWidgetItem) -> None:
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        self._draft.dictionary = [e for e in self._draft.dictionary if e.id != entry_id]
        self._dict_list.takeItem(self._dict_list.row(item))

    # =========================================================== Snippets

    def _build_snippets_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(QLabel("Snippets"))
        layout.addWidget(
            self._caption(
                "Triggers expand into longer text. Use /slash triggers or whole phrases."
            )
        )

        input_row = QHBoxLayout()
        self._snip_trigger = QLineEdit()
        self._snip_trigger.setPlaceholderText("Trigger (e.g. /sig or signature block)")
        self._snip_phrase = QCheckBox("Phrase")
        input_row.addWidget(self._snip_trigger, 2)
        input_row.addWidget(self._snip_phrase)
        layout.addLayout(input_row)

        self._snip_replacement = QTextEdit()
        self._snip_replacement.setPlaceholderText("Replacement")
        self._snip_replacement.setFixedHeight(44)
        layout.addWidget(self._snip_replacement)

        add_btn = QPushButton("Add snippet")
        add_btn.clicked.connect(self._add_snippet)
        layout.addWidget(add_btn)

        self._snip_list = QListWidget()
        self._snip_list.itemDoubleClicked.connect(self._remove_selected_snippet)
        for snip in self._draft.snippets:
            self._append_snippet_item(snip)
        layout.addWidget(self._snip_list, 1)
        layout.addWidget(self._caption("Double-click to remove."))
        return w

    def _append_snippet_item(self, snip: Snippet) -> None:
        label = f"{snip.trigger}  →  {snip.replacement.splitlines()[0][:50] if snip.replacement else ''}"
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, snip.id)
        self._snip_list.addItem(item)

    def _add_snippet(self) -> None:
        trigger = self._snip_trigger.text().strip()
        replacement = self._snip_replacement.toPlainText()
        if not trigger:
            return
        snip = Snippet(
            trigger=trigger,
            replacement=replacement,
            trigger_is_phrase=self._snip_phrase.isChecked(),
        )
        self._draft.snippets.append(snip)
        self._append_snippet_item(snip)
        self._snip_trigger.clear()
        self._snip_replacement.clear()
        self._snip_phrase.setChecked(False)

    def _remove_selected_snippet(self, item: QListWidgetItem) -> None:
        snip_id = item.data(Qt.ItemDataRole.UserRole)
        self._draft.snippets = [s for s in self._draft.snippets if s.id != snip_id]
        self._snip_list.takeItem(self._snip_list.row(item))

    # =========================================================== Advanced

    def _build_advanced_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        _tighten_form(form)

        self._paste_behavior = QComboBox()
        for pb in PasteBehavior:
            self._paste_behavior.addItem(pb.value.replace("_", " ").title(), pb)
        self._paste_behavior.setCurrentIndex(
            list(PasteBehavior).index(self._draft.paste_behavior)
        )
        form.addRow("Insertion method", self._paste_behavior)

        self._restore_clipboard = QCheckBox("Restore clipboard after paste")
        self._restore_clipboard.setChecked(self._draft.restore_clipboard)
        form.addRow("", self._restore_clipboard)

        self._save_audio_history = QCheckBox("Save audio history (off by default)")
        self._save_audio_history.setChecked(self._draft.save_audio_history)
        form.addRow("Privacy", self._save_audio_history)

        self._history_size = QSpinBox()
        self._history_size.setRange(1, 200)
        self._history_size.setValue(self._draft.history_size)
        form.addRow("Keep last N dictations", self._history_size)
        return w

    # ============================================================== helpers

    def _refresh_usage_bar(self) -> None:
        snap: UsageSnapshot = self._usage.snapshot()
        frac = snap.day_fraction
        self._usage_bar.setValue(int(round(frac * 1000)))
        used_min = snap.day_seconds / 60.0
        limit_min = snap.day_limit / 60.0
        remaining_min = max(0.0, limit_min - used_min)
        self._usage_bar.setFormat(
            f"{used_min:.1f} / {limit_min:.0f} min   ({frac * 100:.1f}%)"
        )
        # Color thresholds: green → amber → red.
        if frac >= 0.9:
            color = "#d9534f"  # red
        elif frac >= 0.7:
            color = "#f0ad4e"  # amber
        else:
            color = "#5cb85c"  # green
        self._usage_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #555; border-radius: 4px;"
            " background: #2a2a2a; text-align: center; color: #eee; }"
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
        )
        hour_used_min = snap.hour_seconds / 60.0
        hour_limit_min = snap.hour_limit / 60.0
        self._usage_caption.setText(
            f"{remaining_min:.1f} min left today"
            f"  ·  this hour: {hour_used_min:.1f} / {hour_limit_min:.0f} min"
            "  ·  resets on UTC day boundary. Tracked locally per machine."
        )

    def _caption(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("color: #888;")
        label.setWordWrap(True)
        return label

    # =================================================================== save

    def _save(self) -> None:
        try:
            self._draft.input_device = self._mic_combo.currentData()
            langs: list[str] = []
            if self._lang_en.isChecked():
                langs.append("en")
            if self._lang_pt.isChecked():
                langs.append("pt")
            if not langs:  # never leave it empty — fall back to English
                langs = ["en"]
                self._lang_en.setChecked(True)
            self._draft.languages = langs
            self._draft.dictation_mode = self._mode_combo.currentData()
            self._draft.stt_provider = self._stt_combo.currentData()
            self._secrets.set_groq_key(self._groq_key_field.text().strip())
            self._draft.whisper_model_size = self._whisper_size.currentText()
            self._draft.whisper_compute_type = self._whisper_compute.currentText()

            bindings: list[HotkeyBinding] = []
            for i in range(self._bindings_list.count()):
                payload = self._bindings_list.item(i).data(Qt.ItemDataRole.UserRole)
                bindings.append(HotkeyBinding.model_validate(payload))
            if not bindings:
                bindings = [HotkeyBinding()]
            self._draft.hotkeys = bindings
            self._draft.hotkey_mode = self._hotkey_mode.currentData()
            self._draft.command_mode = self._command_mode.currentData()
            self._draft.confirm_destructive_commands = self._confirm_destructive.isChecked()
            self._draft.paste_behavior = self._paste_behavior.currentData()
            self._draft.restore_clipboard = self._restore_clipboard.isChecked()
            self._draft.save_audio_history = self._save_audio_history.isChecked()
            self._draft.history_size = self._history_size.value()

            self._store.replace(self._draft)
            self._on_save()
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
