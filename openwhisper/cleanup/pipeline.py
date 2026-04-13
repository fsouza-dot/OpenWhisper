"""Orchestrates the full cleanup pass. This is the object the coordinator
calls after it has a raw transcript in hand.

Stays pure: no network, no UI — only the optional injected LLM providers
reach the outside world.
"""
from __future__ import annotations

from typing import Optional

from ..commands.interpreter import RegexCommandInterpreter
from ..logging_setup import get_logger
from ..protocols import CleanupInput, CleanupResult, TextCleanupProvider
from ..settings import AppSettings, DictationMode
from .dictionary import PersonalDictionary
from .heuristic import HeuristicCleanup
from .snippets import SnippetExpander

log = get_logger("cleanup.pipeline")


class CleanupPipeline:
    def __init__(
        self,
        llm_provider: Optional[TextCleanupProvider] = None,
        heuristics: Optional[HeuristicCleanup] = None,
        command_interpreter: Optional[RegexCommandInterpreter] = None,
    ):
        self.llm = llm_provider
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

        # 1. Local: dictionary → snippets → heuristic cleanup.
        text = trimmed
        text = PersonalDictionary(settings.dictionary).apply(text)
        text = SnippetExpander(settings.snippets).expand(text)
        heuristic = self.heuristics.apply(text, settings.dictation_mode)
        text = heuristic.text

        # 2. Regex command fast-path.
        decision = self.commands.interpret(text)
        if decision.command and decision.confidence >= 0.9 and not decision.residual_text:
            return CleanupResult(
                cleaned="",
                command=decision.command,
                confidence=decision.confidence,
            )

        # 3. Decide whether to call the LLM.
        should_skip_llm = (
            rewrite_hint is None
            and decision.command is None
            and settings.dictation_mode == DictationMode.verbatim
            and heuristic.looks_clean
        )

        if should_skip_llm or self.llm is None:
            return CleanupResult(
                cleaned=text,
                command=decision.command,
                confidence=1.0 if decision.command is None else decision.confidence,
                used_llm=False,
            )

        # 4. Primary LLM pass.
        payload = CleanupInput(
            raw_transcript=text,
            mode=settings.dictation_mode,
            dictionary=settings.dictionary,
            snippets=settings.snippets,
            rewrite_hint=rewrite_hint,
        )
        try:
            result = self.llm.clean(payload)
        except Exception as exc:
            log.error("Primary LLM cleanup failed: %s. Falling back to heuristic.", exc)
            return CleanupResult(
                cleaned=text,
                command=decision.command,
                confidence=0.5,
                used_llm=False,
            )

        return result
