"""Zero-cost local cleanup. Runs before we ever consider calling Claude.

Goal: handle 80% of typical dictations so the LLM stays idle. Anything
too risky to do locally (paraphrasing, grammar fixes, tone changes) stays
with the LLM.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

from ..settings import DictationMode


FILLERS: List[str] = ["um", "uh", "erm", "ah", "mm", "uhh", "ehm", "hmm"]


_SPOKEN_PUNCT: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"\s*,?\s*\bcomma\b",            re.IGNORECASE), ","),
    (re.compile(r"\s*,?\s*\bperiod\b",           re.IGNORECASE), "."),
    (re.compile(r"\s*,?\s*\bfull stop\b",        re.IGNORECASE), "."),
    (re.compile(r"\s*,?\s*\bquestion mark\b",    re.IGNORECASE), "?"),
    (re.compile(r"\s*,?\s*\bexclamation mark\b", re.IGNORECASE), "!"),
    (re.compile(r"\s*,?\s*\bexclamation point\b",re.IGNORECASE), "!"),
    (re.compile(r"\s*,?\s*\bcolon\b",            re.IGNORECASE), ":"),
    (re.compile(r"\s*,?\s*\bsemicolon\b",        re.IGNORECASE), ";"),
    (re.compile(r"\s*,?\s*\bopen paren\b",       re.IGNORECASE), " ("),
    (re.compile(r"\s*,?\s*\bclose paren\b",      re.IGNORECASE), ")"),
    (re.compile(r"\s*,?\s*\bopen quote\b",       re.IGNORECASE), ' "'),
    (re.compile(r"\s*,?\s*\bclose quote\b",      re.IGNORECASE), '"'),
    (re.compile(r"\bat sign\b",                  re.IGNORECASE), "@"),
    (re.compile(r"\bhashtag\b",                  re.IGNORECASE), "#"),
    (re.compile(r"\bdot com\b",                  re.IGNORECASE), ".com"),
]

_FILLER_RE = re.compile(r"\b(" + "|".join(FILLERS) + r")\b[,]?", re.IGNORECASE)
_FILLER_CHECK_RE = re.compile(r"\b(um|uh|erm|ah)\b", re.IGNORECASE)
_MULTI_SPACE_RE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT_RE = re.compile(r" +([,.!?;:])")


@dataclass
class HeuristicOutput:
    text: str
    looks_clean: bool


class HeuristicCleanup:
    def apply(self, raw: str, mode: DictationMode) -> HeuristicOutput:
        text = (raw or "").strip()
        if not text:
            return HeuristicOutput(text="", looks_clean=True)

        text = _MULTI_SPACE_RE.sub(" ", text)

        if mode == DictationMode.polished:
            text = _FILLER_RE.sub("", text)
            text = _MULTI_SPACE_RE.sub(" ", text).strip()

        # Capitalize the first letter only if the first word is plain
        # lowercase. Preserving intentional casing (e.g. "OpenWhisper",
        # "iPhone") matters more than enforcing sentence case.
        if text and text[0].isalpha() and text[0].islower():
            first_word_end = 0
            while first_word_end < len(text) and not text[first_word_end].isspace():
                first_word_end += 1
            first_word = text[:first_word_end]
            if first_word.islower():
                text = text[0].upper() + text[1:]

        if mode == DictationMode.polished and text and text[-1] not in ".!?":
            text += "."

        text = self._normalize_spoken_punctuation(text)

        return HeuristicOutput(text=text, looks_clean=self._looks_clean(text))

    def _normalize_spoken_punctuation(self, text: str) -> str:
        result = text
        for pattern, repl in _SPOKEN_PUNCT:
            result = pattern.sub(repl, result)
        result = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", result)
        result = _MULTI_SPACE_RE.sub(" ", result).strip()
        return result

    def _looks_clean(self, text: str) -> bool:
        """Fast path decision: if this returns True *and* the user is in
        verbatim mode *and* there's no command, we skip the LLM entirely."""
        if not text:
            return True
        if len(text) > 300:
            return False
        if len(text.split()) > 40:
            return False
        if text[-1] not in ".!?":
            return False
        if _FILLER_CHECK_RE.search(text):
            return False
        return True
