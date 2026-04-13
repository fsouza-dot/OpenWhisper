"""Convenience launcher so you can `python run.py` from the repo root
without installing the package first.
"""
from __future__ import annotations

from openwhisper.app import run

if __name__ == "__main__":
    raise SystemExit(run())
