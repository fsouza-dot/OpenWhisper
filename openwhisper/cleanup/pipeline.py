"""Orchestrates the full cleanup pass. This is the object the coordinator
calls after it has a raw transcript in hand.
"""
from __future__ import annotations

from typing import Optional

from ..commands.interpreter import RegexCommandInterpreter
from ..logging_setup import get_logger
from ..protocols import CleanupResult
from ..settings import AppSettings, DictationMode
from .heuristic import HeuristicCleanup

log = get_logger("cleanup.pipeline")


class CleanupPipeline:
    def __init__(
        self,
        llm_provider=None,
        heuristics: Optional[HeuristicCleanup] = None,
        command_interpreter: Optional[RegexCommandInterpreter] = None,
    ):
        self.heuristics = heuristics or HeuristicCleanup()
        self.commands = command_interpreter or RegexCommandInterpreter()

    def run(
        self,
        raw_transcript: str,
        settings: AppSettings,
        rewrite_hint: Optional[str] = None,
    ) -> CleanupResult:
        trimmed = (raw_transcript or "").strip()
        if not trimmed:
            return CleanupResult(cleaned="")

        # 1. Heuristic cleanup (capitalization, punctuation)
        heuristic = self.heuristics.apply(trimmed, settings.dictation_mode)
        text = heuristic.text

        # 2. Regex command fast-path
        decision = self.commands.interpret(text)
        if decision.command and decision.confidence >= 0.9 and not decision.residual_text:
            return CleanupResult(
                cleaned="",
                command=decision.command,
                confidence=decision.confidence,
            )

        return CleanupResult(
            cleaned=text,
            command=decision.command,
            confidence=1.0 if decision.command is None else decision.confidence,
            used_llm=False,
        )
