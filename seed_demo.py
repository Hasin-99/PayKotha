#!/usr/bin/env python3
"""Seed demo users for a quick viva / CV demo."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.repositories.excel_store import ExcelStore
from src.services.payment_system import PaymentSystem


def main() -> None:
    data = ROOT / "data"
    system = PaymentSystem(ExcelStore(data))
    system.load()
    if system.users:
        print("Data already exists — skip seed (delete data/*.xlsx to re-seed).")
        return

    alice = system.register_user("Alice Rahman", "01711111111", "1234", opening_balance=2000)
    bob = system.register_user("Bob Hasan", "01722222222", "5678", opening_balance=500)
    system.send_money(alice, bob.phone_number, 250, "Demo transfer")
    system.save()
    print("Seeded demo accounts:")
    print(f"  {alice.name}  {alice.phone_number}  PIN 1234  balance ৳{alice.check_balance():.2f}")
    print(f"  {bob.name}    {bob.phone_number}  PIN 5678  balance ৳{bob.check_balance():.2f}")


if __name__ == "__main__":
    main()
