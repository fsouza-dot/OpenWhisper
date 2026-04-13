"""Groq free-tier usage tracking.

Groq's free tier for `whisper-large-v3-turbo` meters *audio seconds*
transcribed per day (ASD) and per hour (ASH). We record the duration
of every successful Groq request locally so the Settings screen can
show the user how much of their daily allocation is left.

This is a best-effort, local counter. The source of truth is Groq's
own metering — we don't call any usage API. If OpenWhisper is run on
multiple machines with the same key, each machine will see its own
slice of the usage only.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional

from .config import app_data_dir
from .logging_setup import get_logger

log = get_logger("usage")


# Groq free-tier limits for whisper-large-v3-turbo, in audio seconds.
# Source: https://console.groq.com/docs/rate-limits (free tier).
# These are defaults — if Groq changes them, users can live with a
# slightly-off bar until we update this constant.
FREE_TIER_AUDIO_SECONDS_PER_DAY = 28_800   # 8 hours
FREE_TIER_AUDIO_SECONDS_PER_HOUR = 7_200   # 2 hours


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _hour_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")


@dataclass
class UsageSnapshot:
    day_seconds: float
    hour_seconds: float
    day_limit: float = FREE_TIER_AUDIO_SECONDS_PER_DAY
    hour_limit: float = FREE_TIER_AUDIO_SECONDS_PER_HOUR

    @property
    def day_fraction(self) -> float:
        return min(1.0, self.day_seconds / self.day_limit) if self.day_limit else 0.0

    @property
    def hour_fraction(self) -> float:
        return min(1.0, self.hour_seconds / self.hour_limit) if self.hour_limit else 0.0


class UsageTracker:
    """Thread-safe on-disk counter for Groq audio seconds used.

    Schema: a tiny JSON blob at `%APPDATA%/OpenWhisper/usage.json`:

        {"day": "2026-04-11", "day_seconds": 132.4,
         "hour": "2026-04-11T14", "hour_seconds": 41.7}
    """

    def __init__(self, file_path: Optional[Path] = None):
        self._path: Path = file_path or (app_data_dir() / "usage.json")
        self._lock = threading.RLock()
        self._day = _today_utc()
        self._day_seconds = 0.0
        self._hour = _hour_utc()
        self._hour_seconds = 0.0
        self._listeners: List[Callable[[UsageSnapshot], None]] = []
        self._load()

    # ------------------------------------------------------------- persistence

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("Usage file unreadable, resetting: %s", exc)
            return
        if raw.get("day") == self._day:
            self._day_seconds = float(raw.get("day_seconds", 0.0))
        if raw.get("hour") == self._hour:
            self._hour_seconds = float(raw.get("hour_seconds", 0.0))

    def _save_locked(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(
                    {
                        "day": self._day,
                        "day_seconds": round(self._day_seconds, 3),
                        "hour": self._hour,
                        "hour_seconds": round(self._hour_seconds, 3),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            log.warning("Failed to persist usage: %s", exc)

    # ------------------------------------------------------------------- api

    def record_audio_seconds(self, seconds: float) -> None:
        if seconds <= 0:
            return
        with self._lock:
            self._roll_buckets_locked()
            self._day_seconds += seconds
            self._hour_seconds += seconds
            self._save_locked()
            snap = self._snapshot_locked()
        for listener in list(self._listeners):
            try:
                listener(snap)
            except Exception as exc:  # pragma: no cover
                log.warning("Usage listener error: %s", exc)

    def snapshot(self) -> UsageSnapshot:
        with self._lock:
            self._roll_buckets_locked()
            return self._snapshot_locked()

    def subscribe(self, listener: Callable[[UsageSnapshot], None]) -> None:
        self._listeners.append(listener)

    def _roll_buckets_locked(self) -> None:
        today = _today_utc()
        if today != self._day:
            self._day = today
            self._day_seconds = 0.0
        hour = _hour_utc()
        if hour != self._hour:
            self._hour = hour
            self._hour_seconds = 0.0

    def _snapshot_locked(self) -> UsageSnapshot:
        return UsageSnapshot(
            day_seconds=self._day_seconds,
            hour_seconds=self._hour_seconds,
        )
