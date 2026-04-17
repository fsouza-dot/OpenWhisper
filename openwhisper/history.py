"""Tiny bounded ring buffer of recent dictation results. Powers
`undo last dictation` and any future recent-items UI."""
from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, List, Optional


@dataclass
class HistoryEntry:
    raw_transcript: str
    final_text: str
    inserted_into: Optional[str] = None  # process name / window title
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DictationHistory:
    def __init__(self, capacity: int = 20):
        self.capacity = max(1, capacity)
        self._entries: Deque[HistoryEntry] = deque(maxlen=self.capacity)
        self._lock = threading.RLock()

    def record(self, entry: HistoryEntry) -> None:
        with self._lock:
            self._entries.append(entry)

    @property
    def last(self) -> Optional[HistoryEntry]:
        with self._lock:
            return self._entries[-1] if self._entries else None

    def pop_last(self) -> Optional[HistoryEntry]:
        with self._lock:
            return self._entries.pop() if self._entries else None

    def snapshot(self) -> List[HistoryEntry]:
        with self._lock:
            return list(self._entries)
