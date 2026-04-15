"""Settings dialog with Windows 11-style left navigation and card-based layout.
Works on a draft copy of `AppSettings` so the user can cancel.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
import sounddevice as sd
from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..keyring_store import SecretStore
from ..languages import WHISPER_LANGUAGES, get_language_display
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


# Qt.Key -> pynput-style key name, for chord capture.
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


# ==================== Language to Country Code Mapping ====================

# Map language codes to country codes for flag images
# Portuguese uses BR (Brazil) as requested
LANGUAGE_COUNTRY: dict[str, str] = {
    "en": "us",
    "es": "es",
    "fr": "fr",
    "de": "de",
    "it": "it",
    "pt": "br",  # Brazil as requested
    "nl": "nl",
    "pl": "pl",
    "ru": "ru",
    "uk": "ua",
    "ja": "jp",
    "ko": "kr",
    "zh": "cn",
    "ar": "sa",
    "cs": "cz",
    "da": "dk",
    "el": "gr",
    "fi": "fi",
    "he": "il",
    "hi": "in",
    "hu": "hu",
    "id": "id",
    "ms": "my",
    "no": "no",
    "ro": "ro",
    "sk": "sk",
    "sv": "se",
    "th": "th",
    "tr": "tr",
    "vi": "vn",
    "af": "za",
    "az": "az",
    "be": "by",
    "bg": "bg",
    "bn": "bd",
    "bs": "ba",
    "ca": "es",
    "cy": "gb",
    "et": "ee",
    "eu": "es",
    "fa": "ir",
    "gl": "es",
    "gu": "in",
    "hr": "hr",
    "hy": "am",
    "is": "is",
    "ka": "ge",
    "kk": "kz",
    "kn": "in",
    "lt": "lt",
    "lv": "lv",
    "mk": "mk",
    "ml": "in",
    "mn": "mn",
    "mr": "in",
    "mt": "mt",
    "ne": "np",
    "pa": "in",
    "si": "lk",
    "sl": "si",
    "sq": "al",
    "sr": "rs",
    "sw": "ke",
    "ta": "in",
    "te": "in",
    "tl": "ph",
    "ur": "pk",
}


def get_country_code(lang_code: str) -> str:
    """Get country code for a language code."""
    return LANGUAGE_COUNTRY.get(lang_code, lang_code)


# Path to bundled flag images
FLAGS_DIR = Path(__file__).parent.parent / "resources" / "flags"


def get_flag_icon(lang_code: str) -> QIcon:
    """Get flag icon for a language code."""
    country = get_country_code(lang_code)
    flag_path = FLAGS_DIR / f"{country}.png"
    if flag_path.exists():
        return QIcon(str(flag_path))
    return QIcon()


# ==================== Windows 11 Style Constants ====================

_WIN11_COLORS = {
    "bg_window": "#202020",
    "bg_sidebar": "#1a1a1a",
    "bg_content": "#2d2d2d",
    "bg_card": "#3a3a3a",
    "bg_card_hover": "#404040",
    "bg_nav_selected": "#3a3a3a",
    "bg_nav_hover": "#2a2a2a",
    "text_primary": "#ffffff",
    "text_secondary": "#9d9d9d",
    "text_dim": "#6d6d6d",
    "accent": "#60cdff",
    "border": "#454545",
    "input_bg": "#323232",
}

_WIN11_QSS = f"""
* {{
    font-family: "Segoe UI", "Segoe UI Emoji", sans-serif;
}}
QDialog {{
    background-color: {_WIN11_COLORS["bg_window"]};
    color: {_WIN11_COLORS["text_primary"]};
}}
QLabel {{
    color: {_WIN11_COLORS["text_primary"]};
    background: none;
    border: none;
}}
QLineEdit, QComboBox, QSpinBox {{
    background-color: {_WIN11_COLORS["input_bg"]};
    color: {_WIN11_COLORS["text_primary"]};
    border: 1px solid {_WIN11_COLORS["border"]};
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 20px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {_WIN11_COLORS["accent"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {_WIN11_COLORS["text_secondary"]};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {_WIN11_COLORS["bg_card"]};
    color: {_WIN11_COLORS["text_primary"]};
    selection-background-color: {_WIN11_COLORS["accent"]};
    border: 1px solid {_WIN11_COLORS["border"]};
    border-radius: 4px;
}}
QPushButton {{
    background-color: {_WIN11_COLORS["bg_card"]};
    color: {_WIN11_COLORS["text_primary"]};
    border: 1px solid {_WIN11_COLORS["border"]};
    border-radius: 4px;
    padding: 6px 16px;
    min-height: 24px;
}}
QPushButton:hover {{
    background-color: {_WIN11_COLORS["bg_card_hover"]};
}}
QPushButton:pressed {{
    background-color: {_WIN11_COLORS["bg_nav_selected"]};
}}
QPushButton#accentButton {{
    background-color: {_WIN11_COLORS["accent"]};
    color: #000000;
    border: none;
}}
QPushButton#accentButton:hover {{
    background-color: #7ed6ff;
}}
QCheckBox {{
    color: {_WIN11_COLORS["text_primary"]};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 3px;
    border: 2px solid {_WIN11_COLORS["text_secondary"]};
    background-color: transparent;
}}
QCheckBox::indicator:checked {{
    background-color: {_WIN11_COLORS["accent"]};
    border-color: {_WIN11_COLORS["accent"]};
}}
QProgressBar {{
    border: 1px solid {_WIN11_COLORS["border"]};
    border-radius: 4px;
    background: {_WIN11_COLORS["input_bg"]};
    text-align: center;
    color: {_WIN11_COLORS["text_primary"]};
    height: 8px;
}}
QProgressBar::chunk {{
    background-color: {_WIN11_COLORS["accent"]};
    border-radius: 3px;
}}
QScrollArea {{
    background-color: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {_WIN11_COLORS["text_dim"]};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {_WIN11_COLORS["text_secondary"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
QListWidget {{
    background-color: {_WIN11_COLORS["input_bg"]};
    color: {_WIN11_COLORS["text_primary"]};
    border: 1px solid {_WIN11_COLORS["border"]};
    border-radius: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px 10px;
    border-radius: 4px;
}}
QListWidget::item:selected {{
    background-color: {_WIN11_COLORS["accent"]};
    color: #000000;
}}
QListWidget::item:hover:!selected {{
    background-color: {_WIN11_COLORS["bg_card_hover"]};
}}
"""


# ==================== Helper Widgets ====================

class HotkeyCaptureButton(QPushButton):
    """Click, then press a key combination - emits `captured` with the
    resulting HotkeyBinding. Escape cancels."""

    captured = Signal(object)  # HotkeyBinding

    _IDLE_LABEL = "Record new binding..."
    _CAPTURING_LABEL = "Press a key combination (Esc to cancel)"

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


class LanguagePicker(QWidget):
    """Dual-list language picker with flags and arrow buttons."""

    MAX_LANGUAGES = 3
    changed = Signal()

    def __init__(self, selected_codes: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self._selected: list[str] = list(selected_codes)[:self.MAX_LANGUAGES]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Search bar
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search languages...")
        self._search.textChanged.connect(self._filter_available)
        self._search.setClearButtonEnabled(True)
        layout.addWidget(self._search)

        lists_row = QHBoxLayout()
        lists_row.setSpacing(12)

        # Left column - Available
        left_col = QVBoxLayout()
        left_col.setSpacing(6)
        lbl = QLabel("Available")
        left_col.addWidget(lbl)
        self._available_list = QListWidget()
        self._available_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._available_list.setMinimumHeight(260)
        self._available_list.setIconSize(QSize(24, 18))  # 4:3 flag aspect ratio
        self._available_list.itemDoubleClicked.connect(self._add_selected_item)
        left_col.addWidget(self._available_list)
        lists_row.addLayout(left_col, 1)

        # Middle buttons
        btn_col = QVBoxLayout()
        btn_col.setSpacing(8)
        btn_col.addStretch(1)
        self._add_btn = QPushButton(">")
        self._add_btn.setFixedSize(40, 32)
        self._add_btn.setObjectName("accentButton")
        self._add_btn.clicked.connect(self._add_selected)
        btn_col.addWidget(self._add_btn)
        self._remove_btn = QPushButton("<")
        self._remove_btn.setFixedSize(40, 32)
        self._remove_btn.clicked.connect(self._remove_selected)
        btn_col.addWidget(self._remove_btn)
        btn_col.addStretch(1)
        lists_row.addLayout(btn_col)

        # Right column - Selected
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        lbl2 = QLabel("Selected (max 3)")
        right_col.addWidget(lbl2)
        self._selected_list = QListWidget()
        self._selected_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._selected_list.setMinimumHeight(260)
        self._selected_list.setIconSize(QSize(24, 18))  # 4:3 flag aspect ratio
        self._selected_list.itemDoubleClicked.connect(self._remove_selected_item)
        right_col.addWidget(self._selected_list)
        lists_row.addLayout(right_col, 1)

        layout.addLayout(lists_row)

        # Status
        self._status = QLabel()
        self._status.setStyleSheet(f"color: {_WIN11_COLORS['text_secondary']}; background: transparent;")
        layout.addWidget(self._status)

        self._populate_lists()
        self._update_status()

    def _populate_lists(self) -> None:
        self._available_list.clear()
        self._selected_list.clear()
        for code, english, native in WHISPER_LANGUAGES:
            if code not in self._selected:
                item = QListWidgetItem(get_flag_icon(code), get_language_display(code))
                item.setData(Qt.ItemDataRole.UserRole, code)
                self._available_list.addItem(item)
        for code in self._selected:
            item = QListWidgetItem(get_flag_icon(code), get_language_display(code))
            item.setData(Qt.ItemDataRole.UserRole, code)
            self._selected_list.addItem(item)

    def _filter_available(self, text: str) -> None:
        text = text.lower().strip()
        for i in range(self._available_list.count()):
            item = self._available_list.item(i)
            code = item.data(Qt.ItemDataRole.UserRole)
            label = item.text().lower()
            visible = not text or text in label or text in code.lower()
            item.setHidden(not visible)

    def _add_selected(self) -> None:
        item = self._available_list.currentItem()
        if item:
            self._add_selected_item(item)

    def _add_selected_item(self, item: QListWidgetItem) -> None:
        if len(self._selected) >= self.MAX_LANGUAGES:
            return
        code = item.data(Qt.ItemDataRole.UserRole)
        if code not in self._selected:
            self._selected.append(code)
            self._populate_lists()
            self._update_status()
            self.changed.emit()

    def _remove_selected(self) -> None:
        item = self._selected_list.currentItem()
        if item:
            self._remove_selected_item(item)

    def _remove_selected_item(self, item: QListWidgetItem) -> None:
        code = item.data(Qt.ItemDataRole.UserRole)
        if code in self._selected:
            self._selected.remove(code)
            self._populate_lists()
            self._update_status()
            self.changed.emit()

    def _update_status(self) -> None:
        count = len(self._selected)
        if count == 0:
            self._status.setText("Select at least one language (will default to English)")
        elif count == 1:
            self._status.setText("1 language selected (forced mode - fastest)")
        else:
            self._status.setText(f"{count} languages selected (auto-detect per utterance)")
        self._add_btn.setEnabled(count < self.MAX_LANGUAGES)

    def selected_languages(self) -> list[str]:
        return list(self._selected)

    def set_selected(self, codes: list[str]) -> None:
        self._selected = list(codes)[:self.MAX_LANGUAGES]
        self._populate_lists()
        self._update_status()


class SettingCard(QFrame):
    """A Windows 11-style setting card with title, description, and control."""

    def __init__(
        self,
        title: str,
        description: str = "",
        control: QWidget | None = None,
        parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.setObjectName("settingCard")
        self.setStyleSheet(f"""
            QFrame#settingCard {{
                background-color: {_WIN11_COLORS["bg_card"]};
                border-radius: 6px;
            }}
            QFrame#settingCard:hover {{
                background-color: {_WIN11_COLORS["bg_card_hover"]};
            }}
            QFrame#settingCard QLabel {{
                background-color: transparent;
                border: none;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Text section
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        text_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {_WIN11_COLORS['text_primary']}; font-size: 14px; background: transparent;")
        text_layout.addWidget(title_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet(f"color: {_WIN11_COLORS['text_secondary']}; font-size: 12px; background: transparent;")
            desc_label.setWordWrap(True)
            text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)

        if control:
            layout.addWidget(control)


class SectionHeader(QLabel):
    """A Windows 11-style section header."""

    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            color: {_WIN11_COLORS["text_primary"]};
            background: transparent;
            font-size: 14px;
            font-weight: 600;
            padding: 8px 0 4px 0;
            border: none;
        """)


class NavItem(QPushButton):
    """A sidebar navigation item."""

    def __init__(self, icon: str, text: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setText(f"  {icon}  {text}")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)
        self._update_style(False)

    def _update_style(self, selected: bool) -> None:
        if selected:
            bg = _WIN11_COLORS["bg_nav_selected"]
        else:
            bg = "transparent"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {_WIN11_COLORS["text_primary"]};
                border: none;
                border-radius: 6px;
                text-align: left;
                padding-left: 12px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {_WIN11_COLORS["bg_nav_hover"]};
            }}
        """)

    def setChecked(self, checked: bool) -> None:  # noqa: N802
        super().setChecked(checked)
        self._update_style(checked)


# ==================== Main Settings Window ====================

class SettingsWindow(QDialog):
    def __init__(
        self,
        store: SettingsStore,
        secrets: SecretStore,
        usage: UsageTracker,
        on_save: Callable[[], None],
    ):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setMinimumSize(800, 580)
        self.resize(900, 640)
        self.setStyleSheet(_WIN11_QSS)

        self._store = store
        self._secrets = secrets
        self._usage = usage
        self._on_save = on_save
        self._draft: AppSettings = store.settings.model_copy(deep=True)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = self._build_sidebar()
        main_layout.addWidget(sidebar)

        # Content area
        content_container = QWidget()
        content_container.setStyleSheet(f"background-color: {_WIN11_COLORS['bg_content']};")
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Stacked pages
        self._pages = QStackedWidget()
        self._pages.addWidget(self._build_general_page())
        self._pages.addWidget(self._build_languages_page())
        self._pages.addWidget(self._build_microphone_page())
        self._pages.addWidget(self._build_hotkey_page())
        self._pages.addWidget(self._build_advanced_page())
        content_layout.addWidget(self._pages, 1)

        # Footer with save/cancel
        footer = self._build_footer()
        content_layout.addWidget(footer)

        main_layout.addWidget(content_container, 1)

        # State for mic test
        self._test_recording: np.ndarray | None = None
        self._test_stream: sd.InputStream | None = None
        self._test_chunks: list[np.ndarray] = []

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background-color: {_WIN11_COLORS['bg_sidebar']};")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(4)

        # Title
        title = QLabel("Settings")
        title.setStyleSheet(f"""
            color: {_WIN11_COLORS["text_primary"]};
            font-size: 20px;
            font-weight: 600;
            padding: 0 0 20px 8px;
        """)
        layout.addWidget(title)

        # Nav items
        self._nav_items: list[NavItem] = []
        nav_data = [
            ("General", 0),
            ("Languages", 1),
            ("Microphone", 2),
            ("Hotkey", 3),
            ("Advanced", 4),
        ]

        for text, page_idx in nav_data:
            icon = self._get_nav_icon(text)
            item = NavItem(icon, text)
            item.clicked.connect(lambda checked, idx=page_idx: self._switch_page(idx))
            self._nav_items.append(item)
            layout.addWidget(item)

        layout.addStretch(1)

        # Set first page active
        self._nav_items[0].setChecked(True)

        return sidebar

    def _get_nav_icon(self, name: str) -> str:
        icons = {
            "General": "\u2699",     # gear
            "Languages": "\U0001F310",  # globe
            "Microphone": "\U0001F3A4",  # microphone
            "Hotkey": "\u2328",      # keyboard
            "Advanced": "\U0001F527",    # wrench
        }
        return icons.get(name, "\u2022")

    def _switch_page(self, idx: int) -> None:
        self._pages.setCurrentIndex(idx)
        for i, item in enumerate(self._nav_items):
            item.setChecked(i == idx)

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        footer.setStyleSheet(f"background-color: {_WIN11_COLORS['bg_content']};")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(24, 16, 24, 16)

        layout.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("accentButton")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

        return footer

    def _create_page(self, title: str, subtitle: str = "") -> tuple[QWidget, QVBoxLayout]:
        """Create a scrollable page with header."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet(f"background-color: {_WIN11_COLORS['bg_content']};")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(32, 28, 32, 20)
        header_layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {_WIN11_COLORS["text_primary"]};
            background: transparent;
            font-size: 28px;
            font-weight: 600;
        """)
        header_layout.addWidget(title_label)

        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setStyleSheet(f"color: {_WIN11_COLORS['text_secondary']}; background: transparent; font-size: 13px;")
            header_layout.addWidget(sub_label)

        page_layout.addWidget(header)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet(f"background-color: {_WIN11_COLORS['bg_content']};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 0, 32, 32)
        content_layout.setSpacing(12)

        scroll.setWidget(content)
        page_layout.addWidget(scroll, 1)

        return page, content_layout

    # ============================================================= General

    def _build_general_page(self) -> QWidget:
        page, layout = self._create_page("General", "Speech recognition and transcription settings")

        # Dictation section
        layout.addWidget(SectionHeader("Dictation"))

        self._mode_combo = QComboBox()
        self._mode_combo.setFixedWidth(200)
        for m in DictationMode:
            self._mode_combo.addItem(m.value.capitalize(), m)
        self._mode_combo.setCurrentIndex(list(DictationMode).index(self._draft.dictation_mode))
        layout.addWidget(SettingCard(
            "Dictation mode",
            "How text is processed after transcription",
            self._mode_combo
        ))

        # Speech-to-text section
        layout.addWidget(SectionHeader("Speech-to-Text Provider"))

        self._stt_combo = QComboBox()
        self._stt_combo.setFixedWidth(280)
        _STT_LABELS = {
            STTProviderKind.whisper: "Local faster-whisper",
            STTProviderKind.groq: "Groq whisper-large-v3-turbo (cloud)",
        }
        for s in STTProviderKind:
            self._stt_combo.addItem(_STT_LABELS.get(s, s.value), s)
        self._stt_combo.setCurrentIndex(list(STTProviderKind).index(self._draft.stt_provider))
        layout.addWidget(SettingCard(
            "Backend",
            "Groq is fastest but requires internet. Local is offline.",
            self._stt_combo
        ))

        self._groq_key_field = QLineEdit(self._secrets.get_groq_key())
        self._groq_key_field.setEchoMode(QLineEdit.EchoMode.Password)
        self._groq_key_field.setPlaceholderText("gsk_...")
        self._groq_key_field.setFixedWidth(280)
        layout.addWidget(SettingCard(
            "Groq API Key",
            "Get a free key at console.groq.com",
            self._groq_key_field
        ))

        # Usage bar card
        usage_card = QFrame()
        usage_card.setObjectName("usageCard")
        usage_card.setStyleSheet(f"""
            QFrame#usageCard {{
                background-color: {_WIN11_COLORS["bg_card"]};
                border-radius: 6px;
            }}
            QFrame#usageCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        usage_layout = QVBoxLayout(usage_card)
        usage_layout.setContentsMargins(16, 14, 16, 14)
        usage_layout.setSpacing(8)

        usage_title = QLabel("Groq Free Tier Usage (Today)")
        usage_title.setStyleSheet(f"color: {_WIN11_COLORS['text_primary']}; font-size: 14px; background: transparent;")
        usage_layout.addWidget(usage_title)

        self._usage_bar = QProgressBar()
        self._usage_bar.setRange(0, 1000)
        self._usage_bar.setTextVisible(True)
        self._usage_bar.setFixedHeight(20)
        usage_layout.addWidget(self._usage_bar)

        self._usage_caption = QLabel("")
        self._usage_caption.setStyleSheet(f"color: {_WIN11_COLORS['text_dim']}; font-size: 11px; background: transparent;")
        self._usage_caption.setWordWrap(True)
        usage_layout.addWidget(self._usage_caption)

        layout.addWidget(usage_card)
        self._refresh_usage_bar()

        self._usage_timer = QTimer(self)
        self._usage_timer.setInterval(2000)
        self._usage_timer.timeout.connect(self._refresh_usage_bar)
        self._usage_timer.start()

        # Local Whisper settings
        layout.addWidget(SectionHeader("Local Whisper Settings"))

        self._whisper_size = QComboBox()
        self._whisper_size.setFixedWidth(160)
        for size in ["tiny.en", "base.en", "small.en", "medium.en"]:
            self._whisper_size.addItem(size)
        self._whisper_size.setCurrentText(self._draft.whisper_model_size)
        layout.addWidget(SettingCard(
            "Model size",
            "Larger models are more accurate but slower",
            self._whisper_size
        ))

        self._whisper_compute = QComboBox()
        self._whisper_compute.setFixedWidth(160)
        for ct in ["int8", "int8_float16", "float16", "float32"]:
            self._whisper_compute.addItem(ct)
        self._whisper_compute.setCurrentText(self._draft.whisper_compute_type)
        layout.addWidget(SettingCard(
            "Compute type",
            "int8 is fastest on CPU, float16 for CUDA",
            self._whisper_compute
        ))

        layout.addStretch(1)
        return page

    # ========================================================= Languages

    def _build_languages_page(self) -> QWidget:
        page, layout = self._create_page(
            "Languages",
            "Single language = fastest. Multiple = auto-detect per utterance."
        )

        # Language picker
        self._language_picker = LanguagePicker(self._draft.languages)
        layout.addWidget(self._language_picker)

        layout.addStretch(1)
        return page

    # ========================================================= Microphone

    def _build_microphone_page(self) -> QWidget:
        page, layout = self._create_page("Microphone", "Audio input device configuration")

        layout.addWidget(SectionHeader("Input Device"))

        self._mic_combo = QComboBox()
        self._mic_combo.setFixedWidth(300)
        self._populate_mic_devices()
        layout.addWidget(SettingCard(
            "Input device",
            "Select the microphone OpenWhisper should record from",
            self._mic_combo
        ))

        refresh_btn = QPushButton("Refresh device list")
        refresh_btn.clicked.connect(self._populate_mic_devices)
        layout.addWidget(SettingCard(
            "Devices",
            "Rescan for connected audio devices",
            refresh_btn
        ))

        # Test section
        layout.addWidget(SectionHeader("Test Recording"))

        test_card = QFrame()
        test_card.setObjectName("testCard")
        test_card.setStyleSheet(f"""
            QFrame#testCard {{
                background-color: {_WIN11_COLORS["bg_card"]};
                border-radius: 6px;
            }}
            QFrame#testCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        test_layout = QVBoxLayout(test_card)
        test_layout.setContentsMargins(16, 14, 16, 14)
        test_layout.setSpacing(12)

        test_title = QLabel("Microphone Test")
        test_title.setStyleSheet(f"color: {_WIN11_COLORS['text_primary']}; font-size: 14px; background: transparent;")
        test_layout.addWidget(test_title)

        test_desc = QLabel("Record 3 seconds of audio and play it back to verify your microphone is working.")
        test_desc.setStyleSheet(f"color: {_WIN11_COLORS['text_secondary']}; font-size: 12px; background: transparent;")
        test_desc.setWordWrap(True)
        test_layout.addWidget(test_desc)

        self._mic_test_btn = QPushButton("Test microphone")
        self._mic_test_btn.clicked.connect(self._test_microphone)
        test_layout.addWidget(self._mic_test_btn)

        self._mic_test_status = QLabel("")
        self._mic_test_status.setStyleSheet(f"color: {_WIN11_COLORS['text_secondary']}; font-size: 12px; background: transparent;")
        self._mic_test_status.setWordWrap(True)
        test_layout.addWidget(self._mic_test_status)

        layout.addWidget(test_card)

        layout.addStretch(1)
        return page

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
        current = self._draft.input_device
        if current:
            idx = self._mic_combo.findData(current)
            if idx >= 0:
                self._mic_combo.setCurrentIndex(idx)
        self._mic_combo.blockSignals(False)

    def _test_microphone(self) -> None:
        if self._test_stream is not None:
            return
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

        def callback(indata, frames, time_info, status):
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
        self._mic_test_status.setText("Recording 3 seconds - speak now...")
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
            f"Captured {len(samples) / sample_rate:.1f}s - peak {peak:.3f}, "
            f"RMS {rms:.4f}. Playing back..."
        )

        try:
            sd.play(samples, samplerate=sample_rate)
        except Exception as exc:
            self._mic_test_status.setText(f"Recorded OK but playback failed: {exc}")
            self._mic_test_btn.setEnabled(True)
            return

        playback_ms = int((len(samples) / sample_rate) * 1000) + 250
        QTimer.singleShot(playback_ms, lambda: (
            self._mic_test_btn.setEnabled(True),
            self._mic_test_status.setText(
                self._mic_test_status.text().replace("Playing back...", "Done.")
                + ("  (silent - input level was 0)" if peak == 0 else "")
            ),
        ))

    # ============================================================= Hotkey

    def _build_hotkey_page(self) -> QWidget:
        page, layout = self._create_page("Hotkey", "Configure keyboard shortcuts for dictation")

        layout.addWidget(SectionHeader("Mode"))

        self._hotkey_mode = QComboBox()
        self._hotkey_mode.setFixedWidth(200)
        for hm in HotkeyMode:
            self._hotkey_mode.addItem(hm.value.replace("_", " ").title(), hm)
        self._hotkey_mode.setCurrentIndex(list(HotkeyMode).index(self._draft.hotkey_mode))
        layout.addWidget(SettingCard(
            "Hotkey mode",
            "Push-to-talk or toggle behavior",
            self._hotkey_mode
        ))

        self._command_mode = QComboBox()
        self._command_mode.setFixedWidth(200)
        for cm in CommandModeSetting:
            self._command_mode.addItem(cm.value.replace("_", " ").title(), cm)
        self._command_mode.setCurrentIndex(list(CommandModeSetting).index(self._draft.command_mode))
        layout.addWidget(SettingCard(
            "Command mode",
            "How voice commands are processed",
            self._command_mode
        ))

        # Bindings section
        layout.addWidget(SectionHeader("Key Bindings"))

        bindings_card = QFrame()
        bindings_card.setObjectName("bindingsCard")
        bindings_card.setStyleSheet(f"""
            QFrame#bindingsCard {{
                background-color: {_WIN11_COLORS["bg_card"]};
                border-radius: 6px;
            }}
            QFrame#bindingsCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        bindings_layout = QVBoxLayout(bindings_card)
        bindings_layout.setContentsMargins(16, 14, 16, 14)
        bindings_layout.setSpacing(12)

        bindings_title = QLabel("Active Bindings")
        bindings_title.setStyleSheet(f"color: {_WIN11_COLORS['text_primary']}; font-size: 14px; background: transparent;")
        bindings_layout.addWidget(bindings_title)

        bindings_desc = QLabel("Any of these chords starts a dictation. Add as many as you like.")
        bindings_desc.setStyleSheet(f"color: {_WIN11_COLORS['text_secondary']}; font-size: 12px; background: transparent;")
        bindings_layout.addWidget(bindings_desc)

        self._bindings_list = QListWidget()
        self._bindings_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._bindings_list.setFixedHeight(120)
        for binding in self._draft.hotkeys:
            self._append_binding_item(binding)
        bindings_layout.addWidget(self._bindings_list)

        btn_row = QHBoxLayout()
        self._capture_btn = HotkeyCaptureButton()
        self._capture_btn.captured.connect(self._on_binding_captured)
        btn_row.addWidget(self._capture_btn, 1)

        remove_btn = QPushButton("Remove selected")
        remove_btn.clicked.connect(self._remove_selected_binding)
        btn_row.addWidget(remove_btn)
        bindings_layout.addLayout(btn_row)

        layout.addWidget(bindings_card)

        # Options
        layout.addWidget(SectionHeader("Options"))

        self._confirm_destructive = QCheckBox()
        self._confirm_destructive.setChecked(self._draft.confirm_destructive_commands)
        layout.addWidget(SettingCard(
            "Confirm destructive commands",
            "Ask for confirmation before send, delete, or undo",
            self._confirm_destructive
        ))

        layout.addStretch(1)
        return page

    def _append_binding_item(self, binding: HotkeyBinding) -> None:
        item = QListWidgetItem(binding.display())
        item.setData(Qt.ItemDataRole.UserRole, binding.model_dump())
        self._bindings_list.addItem(item)

    def _on_binding_captured(self, binding: HotkeyBinding) -> None:
        payload = binding.model_dump()
        for i in range(self._bindings_list.count()):
            if self._bindings_list.item(i).data(Qt.ItemDataRole.UserRole) == payload:
                return
        self._append_binding_item(binding)

    def _remove_selected_binding(self) -> None:
        row = self._bindings_list.currentRow()
        if row >= 0:
            self._bindings_list.takeItem(row)

    # =========================================================== Advanced

    def _build_advanced_page(self) -> QWidget:
        page, layout = self._create_page("Advanced", "Text insertion and privacy settings")

        layout.addWidget(SectionHeader("Text Insertion"))

        self._paste_behavior = QComboBox()
        self._paste_behavior.setFixedWidth(200)
        for pb in PasteBehavior:
            self._paste_behavior.addItem(pb.value.replace("_", " ").title(), pb)
        self._paste_behavior.setCurrentIndex(list(PasteBehavior).index(self._draft.paste_behavior))
        layout.addWidget(SettingCard(
            "Insertion method",
            "How transcribed text is inserted into applications",
            self._paste_behavior
        ))

        self._restore_clipboard = QCheckBox()
        self._restore_clipboard.setChecked(self._draft.restore_clipboard)
        layout.addWidget(SettingCard(
            "Restore clipboard after paste",
            "Preserve your clipboard contents after text insertion",
            self._restore_clipboard
        ))

        # Privacy section
        layout.addWidget(SectionHeader("Privacy"))

        self._save_audio_history = QCheckBox()
        self._save_audio_history.setChecked(self._draft.save_audio_history)
        layout.addWidget(SettingCard(
            "Save audio history",
            "Store recorded audio clips locally (off by default)",
            self._save_audio_history
        ))

        self._history_size = QSpinBox()
        self._history_size.setRange(1, 200)
        self._history_size.setValue(self._draft.history_size)
        self._history_size.setFixedWidth(100)
        layout.addWidget(SettingCard(
            "History size",
            "Number of recent dictations to keep",
            self._history_size
        ))

        layout.addStretch(1)
        return page

    # ============================================================== helpers

    def _refresh_usage_bar(self) -> None:
        snap: UsageSnapshot = self._usage.snapshot()
        frac = snap.day_fraction
        self._usage_bar.setValue(int(round(frac * 1000)))
        used_min = snap.day_seconds / 60.0
        limit_min = snap.day_limit / 60.0
        remaining_min = max(0.0, limit_min - used_min)
        self._usage_bar.setFormat(
            f"{used_min:.1f} / {limit_min:.0f} min ({frac * 100:.1f}%)"
        )
        if frac >= 0.9:
            color = "#d9534f"
        elif frac >= 0.7:
            color = "#f0ad4e"
        else:
            color = _WIN11_COLORS["accent"]
        self._usage_bar.setStyleSheet(
            f"QProgressBar {{ border: 1px solid {_WIN11_COLORS['border']}; border-radius: 4px;"
            f" background: {_WIN11_COLORS['input_bg']}; text-align: center; color: #eee; }}"
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
        )
        hour_used_min = snap.hour_seconds / 60.0
        hour_limit_min = snap.hour_limit / 60.0
        self._usage_caption.setText(
            f"{remaining_min:.1f} min left today  |  "
            f"This hour: {hour_used_min:.1f} / {hour_limit_min:.0f} min  |  "
            "Resets on UTC day boundary"
        )

    # =================================================================== save

    def _save(self) -> None:
        try:
            self._draft.input_device = self._mic_combo.currentData()
            langs = self._language_picker.selected_languages()
            if not langs:
                langs = ["en"]
                self._language_picker.set_selected(["en"])
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
