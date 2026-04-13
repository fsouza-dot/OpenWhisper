"""Text expansion. Two trigger flavors:

- Slash triggers (e.g. `/sig`). STT usually hears "slash sig" so we
  normalize "slash X" → "/X" before matching.
- Phrase triggers: the whole phrase is matched and replaced.
"""
from __future__ import annotations

import re
from typing import List

from ..settings import Snippet


_SPOKEN_SLASH_RE = re.compile(r"\bslash\s+([A-Za-z][A-Za-z0-9_\-]*)", re.IGNORECASE)


class SnippetExpander:
    def __init__(self, snippets: List[Snippet]):
        # Longest triggers first to avoid partial shadowing ("hi" vs "hi there").
        self.snippets = sorted(snippets, key=lambda s: len(s.trigger), reverse=True)

    def expand(self, text: str) -> str:
        if not text:
            return text
        result = _SPOKEN_SLASH_RE.sub(lambda m: "/" + m.group(1), text)
        for snip in self.snippets:
            result = self._replace(result, snip)
        return result

    def _replace(self, text: str, snip: Snippet) -> str:
        escaped = re.escape(snip.trigger)
        if snip.trigger_is_phrase:
            pattern = r"\b" + escaped + r"\b"
        else:
            pattern = r"(?<![A-Za-z0-9_])" + escaped + r"(?![A-Za-z0-9_])"
        return re.sub(pattern, lambda _m: snip.replacement, text, flags=re.IGNORECASE)
