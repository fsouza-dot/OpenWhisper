"""Personal dictionary: alias → canonical-term substitution on transcripts.

Strategy:
- Exact alias matching with word-boundary regex.
- Case-insensitive by default; optional case-sensitive per entry.
- Fuzzy matching is intentionally NOT done here — it has a real false-positive
  cost. Users can always add more aliases.
"""
from __future__ import annotations

import re
from typing import List, Pattern, Tuple

from ..settings import DictionaryEntry

MAX_STT_HINTS = 200


class PersonalDictionary:
    def __init__(self, entries: List[DictionaryEntry]):
        self.entries = list(entries)
        self._compiled_patterns: List[Tuple[Pattern, str]] = []
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for all aliases to avoid recompilation."""
        self._compiled_patterns.clear()
        for entry in self.entries:
            for alias in entry.aliases:
                if not alias:
                    continue
                flags = 0 if entry.case_sensitive else re.IGNORECASE
                pattern = re.compile(r"\b" + re.escape(alias) + r"\b", flags)
                self._compiled_patterns.append((pattern, entry.term))

    def apply(self, text: str) -> str:
        if not self._compiled_patterns or not text:
            return text
        result = text
        for pattern, replacement in self._compiled_patterns:
            result = pattern.sub(replacement, result)
        return result

    def stt_hints(self) -> List[str]:
        """Terms to feed the STT backend as bias hints. Include aliases so
        whisper doesn't hallucinate something completely different.

        Capped at MAX_STT_HINTS to avoid exceeding API limits.
        """
        seen: set[str] = set()
        out: list[str] = []
        for entry in self.entries:
            for word in (entry.term, *entry.aliases):
                if word and word not in seen:
                    seen.add(word)
                    out.append(word)
                    if len(out) >= MAX_STT_HINTS:
                        return out
        return out
