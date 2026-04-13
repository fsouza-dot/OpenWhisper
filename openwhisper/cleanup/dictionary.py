"""Personal dictionary: alias → canonical-term substitution on transcripts.

Strategy:
- Exact alias matching with word-boundary regex.
- Case-insensitive by default; optional case-sensitive per entry.
- Fuzzy matching is intentionally NOT done here — it has a real false-positive
  cost. Users can always add more aliases.
"""
from __future__ import annotations

import re
from typing import List

from ..settings import DictionaryEntry


class PersonalDictionary:
    def __init__(self, entries: List[DictionaryEntry]):
        self.entries = list(entries)

    def apply(self, text: str) -> str:
        if not self.entries or not text:
            return text
        result = text
        for entry in self.entries:
            for alias in entry.aliases:
                if not alias:
                    continue
                flags = 0 if entry.case_sensitive else re.IGNORECASE
                pattern = r"\b" + re.escape(alias) + r"\b"
                result = re.sub(pattern, lambda _m: entry.term, result, flags=flags)
        return result

    def stt_hints(self) -> List[str]:
        """Terms to feed the STT backend as bias hints. Include aliases so
        whisper doesn't hallucinate something completely different."""
        seen: set[str] = set()
        out: list[str] = []
        for entry in self.entries:
            for word in (entry.term, *entry.aliases):
                if word and word not in seen:
                    seen.add(word)
                    out.append(word)
        return out
