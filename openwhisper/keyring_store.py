"""Thin wrapper over the `keyring` package. On Windows this hits the
Credential Manager, so the API key is never written to disk in plain text.
"""
from __future__ import annotations

import keyring

from .config import KEYRING_GROQ_ACCOUNT, KEYRING_SERVICE
from .logging_setup import get_logger

log = get_logger("keyring")


class SecretStore:
    def __init__(self, service: str = KEYRING_SERVICE):
        self.service = service

    def get_groq_key(self) -> str:
        try:
            return keyring.get_password(self.service, KEYRING_GROQ_ACCOUNT) or ""
        except Exception as exc:
            log.warning("Keyring read failed (groq): %s", exc)
            return ""

    def set_groq_key(self, value: str) -> None:
        try:
            if value:
                keyring.set_password(self.service, KEYRING_GROQ_ACCOUNT, value)
            else:
                try:
                    keyring.delete_password(self.service, KEYRING_GROQ_ACCOUNT)
                except keyring.errors.PasswordDeleteError:
                    pass
        except Exception as exc:
            log.error("Keyring write failed (groq): %s", exc)
