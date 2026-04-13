"""Entry point: `python -m openwhisper` or the `openwhisper` console script."""
from __future__ import annotations

import sys

from .app import run


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
