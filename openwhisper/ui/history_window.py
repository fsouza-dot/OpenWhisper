"""History window with correction learning.

Shows recent transcriptions and allows users to correct them.
When a correction is made, offers to add word-level differences
as dictionary aliases for future transcriptions.
"""
from __future__ import annotations

import difflib
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..history import DictationHistory, HistoryEntry
from ..settings import DictionaryEntry, SettingsStore

# Windows 11 style colors
_COLORS = {
    "bg": "#1f1f1f",
    "bg_card": "#2d2d2d",
    "text": "#ffffff",
    "text_secondary": "#888888",
    "accent": "#60cdff",
    "border": "#404040",
}


def find_word_corrections(original: str, corrected: str) -> List[Tuple[str, str]]:
    """Find word-level differences between original and corrected text.

    Returns list of (wrong_word, correct_word) tuples.
    """
    if original.strip() == corrected.strip():
        return []

    orig_words = original.split()
    corr_words = corrected.split()

    corrections: List[Tuple[str, str]] = []

    # Use difflib to find matching blocks
    matcher = difflib.SequenceMatcher(None, orig_words, corr_words)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace":
            # Words were replaced - these are potential corrections
            orig_chunk = orig_words[i1:i2]
            corr_chunk = corr_words[j1:j2]

            # If same number of words, pair them up
            if len(orig_chunk) == len(corr_chunk):
                for orig, corr in zip(orig_chunk, corr_chunk):
                    # Only add if they're different (case-insensitive check for non-trivial changes)
                    orig_clean = orig.strip(".,!?;:'\"").lower()
                    corr_clean = corr.strip(".,!?;:'\"").lower()
                    if orig_clean != corr_clean and len(orig_clean) > 1 and len(corr_clean) > 1:
                        corrections.append((orig.strip(".,!?;:'\""), corr.strip(".,!?;:'\"").title()))

    return corrections


class HistoryWindow(QDialog):
    """Window showing dictation history with correction learning."""

    def __init__(
        self,
        history: DictationHistory,
        settings_store: SettingsStore,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._history = history
        self._settings_store = settings_store
        self._current_entry: Optional[HistoryEntry] = None

        self.setWindowTitle("Dictation History")
        self.setMinimumSize(700, 500)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {_COLORS["bg"]};
                color: {_COLORS["text"]};
            }}
            QListWidget {{
                background-color: {_COLORS["bg_card"]};
                border: 1px solid {_COLORS["border"]};
                border-radius: 6px;
                color: {_COLORS["text"]};
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {_COLORS["accent"]};
                color: #000000;
            }}
            QListWidget::item:hover {{
                background-color: #3d3d3d;
            }}
            QTextEdit, QLineEdit {{
                background-color: {_COLORS["bg_card"]};
                border: 1px solid {_COLORS["border"]};
                border-radius: 6px;
                color: {_COLORS["text"]};
                padding: 8px;
            }}
            QLabel {{
                color: {_COLORS["text"]};
            }}
            QPushButton {{
                background-color: {_COLORS["accent"]};
                color: #000000;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #7dd8ff;
            }}
            QPushButton:disabled {{
                background-color: #404040;
                color: #666666;
            }}
        """)

        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Left side: history list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        list_label = QLabel("Recent Dictations")
        list_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {_COLORS['text']};")
        left_layout.addWidget(list_label)

        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self._list)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_list)
        left_layout.addWidget(refresh_btn)

        # Right side: edit panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Original text (read-only)
        orig_label = QLabel("Original Transcription")
        orig_label.setStyleSheet(f"font-size: 12px; color: {_COLORS['text_secondary']};")
        right_layout.addWidget(orig_label)

        self._original_text = QTextEdit()
        self._original_text.setReadOnly(True)
        self._original_text.setMaximumHeight(100)
        right_layout.addWidget(self._original_text)

        # Corrected text (editable)
        corr_label = QLabel("Corrected Text (edit to teach new words)")
        corr_label.setStyleSheet(f"font-size: 12px; color: {_COLORS['text_secondary']};")
        right_layout.addWidget(corr_label)

        self._corrected_text = QTextEdit()
        self._corrected_text.setMaximumHeight(100)
        self._corrected_text.textChanged.connect(self._on_text_changed)
        right_layout.addWidget(self._corrected_text)

        # Detected corrections
        detect_label = QLabel("Detected Word Corrections")
        detect_label.setStyleSheet(f"font-size: 12px; color: {_COLORS['text_secondary']};")
        right_layout.addWidget(detect_label)

        self._corrections_list = QListWidget()
        self._corrections_list.setMaximumHeight(120)
        right_layout.addWidget(self._corrections_list)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._learn_btn = QPushButton("Add to Dictionary")
        self._learn_btn.setEnabled(False)
        self._learn_btn.clicked.connect(self._on_learn_clicked)
        btn_layout.addWidget(self._learn_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(f"""
            background-color: {_COLORS["bg_card"]};
            color: {_COLORS["text"]};
            border: 1px solid {_COLORS["border"]};
        """)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        right_layout.addLayout(btn_layout)
        right_layout.addStretch()

        # Add panels to splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([250, 450])

        layout.addWidget(splitter)

    def _refresh_list(self) -> None:
        self._list.clear()
        entries = self._history.snapshot()

        if not entries:
            item = QListWidgetItem("No dictations yet")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(item)
            return

        # Show newest first
        for entry in reversed(entries):
            preview = entry.final_text[:50] + "..." if len(entry.final_text) > 50 else entry.final_text
            preview = preview.replace("\n", " ")

            time_str = entry.timestamp.strftime("%H:%M:%S")
            item = QListWidgetItem(f"[{time_str}] {preview}")
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self._list.addItem(item)

    def _on_selection_changed(self, current: QListWidgetItem, _prev: QListWidgetItem) -> None:
        if current is None:
            self._current_entry = None
            self._original_text.clear()
            self._corrected_text.clear()
            self._corrections_list.clear()
            return

        entry = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(entry, HistoryEntry):
            return

        self._current_entry = entry
        self._original_text.setPlainText(entry.final_text)
        self._corrected_text.setPlainText(entry.final_text)
        self._corrections_list.clear()
        self._learn_btn.setEnabled(False)

    def _on_text_changed(self) -> None:
        if self._current_entry is None:
            return

        original = self._current_entry.final_text
        corrected = self._corrected_text.toPlainText()

        corrections = find_word_corrections(original, corrected)

        self._corrections_list.clear()
        for wrong, right in corrections:
            item = QListWidgetItem(f'"{wrong}" → "{right}"')
            item.setData(Qt.ItemDataRole.UserRole, (wrong, right))
            item.setCheckState(Qt.CheckState.Checked)
            self._corrections_list.addItem(item)

        self._learn_btn.setEnabled(len(corrections) > 0)

    def _on_learn_clicked(self) -> None:
        # Collect checked corrections
        to_learn: List[Tuple[str, str]] = []
        for i in range(self._corrections_list.count()):
            item = self._corrections_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                data = item.data(Qt.ItemDataRole.UserRole)
                if data:
                    to_learn.append(data)

        if not to_learn:
            return

        # Add to dictionary
        settings = self._settings_store.settings
        dictionary = list(settings.dictionary)

        added_count = 0
        for wrong, right in to_learn:
            # Check if term already exists
            existing = next((e for e in dictionary if e.term.lower() == right.lower()), None)
            if existing:
                # Add alias to existing entry if not already present
                if wrong.lower() not in [a.lower() for a in existing.aliases]:
                    existing.aliases.append(wrong)
                    added_count += 1
            else:
                # Create new entry
                dictionary.append(DictionaryEntry(
                    term=right,
                    aliases=[wrong],
                ))
                added_count += 1

        if added_count > 0:
            # Save settings
            new_settings = settings.model_copy(update={"dictionary": dictionary})
            self._settings_store.replace(new_settings)

            QMessageBox.information(
                self,
                "Dictionary Updated",
                f"Added {added_count} correction(s) to dictionary.\n\n"
                f"Future transcriptions will automatically correct these words.",
            )

            # Clear the corrections list
            self._corrections_list.clear()
            self._learn_btn.setEnabled(False)
