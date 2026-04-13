"""Regex-based command interpreter. Runs before we decide whether to call
Claude so that trivial commands cost nothing and add no latency.

Ordering matters: longest / most specific phrases come first so that
"new paragraph" beats "new ...".
"""
from __future__ import annotations

import re
from typing import List, Pattern, Tuple

from ..protocols import CommandDecision
from .command import DictationCommand


PhraseTable = List[Tuple[Pattern[str], DictationCommand]]


def _build_table() -> PhraseTable:
    pairs: list[tuple[str, DictationCommand]] = [
        (r"\bnew\s+paragraph\b",                 DictationCommand.new_paragraph),
        (r"\bnew\s+line\b",                      DictationCommand.new_line),
        (r"\bbullet(?:ed)?\s+list\b",            DictationCommand.bullet_list),
        (r"\bnumbered\s+list\b",                 DictationCommand.numbered_list),
        (r"\bundo\s+last\s+dictation\b",         DictationCommand.undo_last_dictation),
        (r"\bmake\s+(?:this|it)\s+shorter\b",    DictationCommand.make_shorter),
        (r"\brewrite\s+professionally\b",        DictationCommand.rewrite_professional),
        (r"\brewrite\s+casually\b",              DictationCommand.rewrite_casual),
        (r"\bpress\s+enter\b",                   DictationCommand.press_enter),
        (r"\bpress\s+tab\b",                     DictationCommand.press_tab),
        (r"\bpress\s+escape\b",                  DictationCommand.press_escape),
        (r"\bdelete\s+last\b",                   DictationCommand.delete_last),
        (r"\bsend\s+(?:it|message|this)\b",      DictationCommand.send),
    ]
    return [(re.compile(p, re.IGNORECASE), c) for p, c in pairs]


class RegexCommandInterpreter:
    """Cheap, deterministic first pass. Returns low-confidence when the
    command phrase is embedded in a longer utterance so the coordinator
    can escalate to the LLM for arbitration.
    """

    def __init__(self) -> None:
        self._table: PhraseTable = _build_table()

    def interpret(self, text: str) -> CommandDecision:
        trimmed = (text or "").strip()
        if not trimmed:
            return CommandDecision(command=None, residual_text="", confidence=1.0)

        for pattern, cmd in self._table:
            match = pattern.search(trimmed)
            if not match:
                continue
            leftover = (trimmed[: match.start()] + trimmed[match.end():]).strip(
                " \t\r\n.,;:!?"
            )
            if not leftover:
                return CommandDecision(command=cmd.value, residual_text="", confidence=0.95)
            # Mixed utterance: we're less sure this is a command.
            return CommandDecision(command=cmd.value, residual_text=leftover, confidence=0.55)

        return CommandDecision(command=None, residual_text=trimmed, confidence=1.0)
