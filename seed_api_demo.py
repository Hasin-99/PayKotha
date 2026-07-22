#!/usr/bin/env python3
"""Seed demo customers + dual ops admins (maker-checker)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.app.core.database import SessionLocal, init_db
from backend.app.services.demo_seed import seed_demo_users


def main() -> None:
    Path("data").mkdir(exist_ok=True)
    init_db()
    db = SessionLocal()
    try:
        info = seed_demo_users(db)
        print("Demo seed ready:")
        print(f"  Alice {info['alice']} PIN 1234")
        print(f"  Bob   {info['bob']} PIN 5678")
        print(f"  Maker {info['maker']} PIN 111111")
        print(f"  Checker {info['checker']} PIN 222222")
        print("  Bootstrap admin 01999999999 PIN 999999")
    finally:
        db.close()


if __name__ == "__main__":
    main()
