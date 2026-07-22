#!/usr/bin/env python3
"""PayKotha entry point — Mobile Payment System (bKash simulation)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cli.app import PayKothaCLI


def main() -> None:
    data_dir = ROOT / "data"
    PayKothaCLI(data_dir).run()


if __name__ == "__main__":
    main()
