from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models import Wallet
from src.repositories.excel_store import ExcelStore
from src.services.payment_system import PaymentSystem
from src.utils.validators import normalize_phone, validate_phone


def test_wallet_insufficient_funds():
    w = Wallet(100)
    with pytest.raises(ValueError, match="Insufficient"):
        w.withdraw_funds(150)


def test_wallet_roundtrip():
    w = Wallet(0)
    w.add_funds(200.555)
    assert w.check_balance() == 200.56
    w.withdraw_funds(50.56)
    assert w.check_balance() == 150.0


def test_phone_normalize():
    assert normalize_phone("+8801712345678") == "01712345678"
    assert validate_phone("01712345678") == "01712345678"


def test_p2p_transfer(tmp_path):
    system = PaymentSystem(ExcelStore(tmp_path))
    alice = system.register_user("Alice", "01711111111", "1234", opening_balance=500)
    bob = system.register_user("Bob", "01722222222", "5678", opening_balance=0)
    txn = system.send_money(alice, bob.phone_number, 150, "Lunch")
    assert alice.check_balance() == 350
    assert bob.check_balance() == 150
    assert txn.amount == 150
    system.save()

    system2 = PaymentSystem(ExcelStore(tmp_path))
    system2.load()
    assert system2.get_user(alice.user_id).check_balance() == 350
    assert len(system2.transactions) >= 2  # opening + send


def test_cash_out_fee(tmp_path):
    system = PaymentSystem(ExcelStore(tmp_path))
    u = system.register_user("Carol", "01733333333", "9999", opening_balance=1000)
    system.cash_out(u, 100)
    # 100 + 1.8% fee = 101.8
    assert u.check_balance() == 898.2
