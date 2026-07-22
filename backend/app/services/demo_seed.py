"""Idempotent demo seed — Alice/Bob + dual ops admins for portfolio demos."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import hash_pin
from backend.app.db.models import KycLevel, User
from backend.app.services import wallet_service


def _ensure_admin(db: Session, name: str, phone: str, pin: str) -> User:
    phone = wallet_service.validate_phone(phone)
    row = db.scalar(select(User).where(User.phone == phone))
    if row:
        row.is_admin = True
        row.kyc_level = KycLevel.L2_FULL.value
        db.commit()
        return row
    admin = User(
        id=f"ADM{phone[-4:]}",
        name=name,
        phone=phone,
        pin_hash=hash_pin(pin),
        balance=0.0,
        daily_limit=1_000_000.0,
        is_admin=True,
        kyc_level=KycLevel.L2_FULL.value,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def seed_demo_users(db: Session) -> dict[str, str]:
    """Ensure system, bootstrap admin, maker/checker, and Alice/Bob exist."""
    wallet_service.ensure_system_user(db)
    wallet_service.bootstrap_admin(db)
    maker = _ensure_admin(db, "Ops Maker", "01999999991", "111111")
    checker = _ensure_admin(db, "Ops Checker", "01999999992", "222222")

    existing = db.scalar(select(User).where(User.phone == "01711111111"))
    if not existing:
        alice = wallet_service.register_user(
            db, "Alice Rahman", "01711111111", "1234", 15000, nid_number="1990123456789"
        )
        bob = wallet_service.register_user(
            db, "Bob Hasan", "01722222222", "5678", 5000, nid_number="1990987654321"
        )
        wallet_service.upgrade_kyc(db, alice, KycLevel.L1_NID.value, "1990123456789")
        wallet_service.upgrade_kyc(db, bob, KycLevel.L1_NID.value, "1990987654321")
        wallet_service.send_money(db, alice, bob.phone, 250, "Demo transfer")

    return {
        "maker": maker.phone,
        "checker": checker.phone,
        "alice": "01711111111",
        "bob": "01722222222",
    }
