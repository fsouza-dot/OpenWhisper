"""Spoken commands OpenWhisper understands."""
from __future__ import annotations

from enum import Enum


class DictationCommand(str, Enum):
    new_line = "new_line"
    new_paragraph = "new_paragraph"
    bullet_list = "bullet_list"
    numbered_list = "numbered_list"
    undo_last_dictation = "undo_last_dictation"
    make_shorter = "make_shorter"
    rewrite_professional = "rewrite_professional"
    rewrite_casual = "rewrite_casual"
    send = "send"
    press_enter = "press_enter"
    press_tab = "press_tab"
    press_escape = "press_escape"
    delete_last = "delete_last"

    @property
    def is_destructive(self) -> bool:
        return self in {
            DictationCommand.send,
            DictationCommand.press_enter,
            DictationCommand.delete_last,
            DictationCommand.undo_last_dictation,
        }

    @property
    def auto_execute_threshold(self) -> float:
        return 0.9 if self.is_destructive else 0.65
