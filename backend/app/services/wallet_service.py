from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.security import hash_pin, verify_pin
from backend.app.db.models import (
    Favorite,
    KycLevel,
    LedgerEntry,
    MoneyRequest,
    Notification,
    RequestStatus,
    Transaction,
    TxnStatus,
    TxnType,
    User,
)
from backend.app.services.audit import audit
from backend.app.services.otp_service import verify_otp
from backend.app.services.rails import get_rail
from backend.app.services import redis_client
from backend.app.services import live_bus


BD_PHONE_RE = re.compile(r"^(?:\+8801|8801|01)[3-9]\d{8}$")
SYSTEM_ID = "SYSTEM"
MERCHANT_ID = "MERCHANT"
BILLER_ID = "BILLER"
BANK_ID = "BANK"
SERVICE_IDS = {SYSTEM_ID, MERCHANT_ID, BILLER_ID, BANK_ID}

def _live(user_ids: list[str], kind: str, **extra) -> None:
    payload = {"type": kind, **extra}
    for uid in user_ids:
        if uid and uid not in SERVICE_IDS:
            live_bus.publish(uid, payload)


# Per-KYC single-txn and wallet caps (BDT) — sandbox policy mirroring MFS tiers
KYC_LIMITS = {
    KycLevel.L0_BASIC.value: {"per_txn": 5000.0, "wallet_max": 20000.0, "daily": 25000.0},
    KycLevel.L1_NID.value: {"per_txn": 25000.0, "wallet_max": 100000.0, "daily": 100000.0},
    KycLevel.L2_FULL.value: {"per_txn": 200000.0, "wallet_max": 500000.0, "daily": 500000.0},
}

OPERATORS = {"Grameenphone", "Robi", "Banglalink", "Teletalk", "Airtel"}
BILLERS = {
    "DESCO": "Electricity (DESCO)",
    "NESCO": "Electricity (NESCO)",
    "TITAS": "Gas (Titas)",
    "WASA": "Water (WASA)",
    "LINK3": "Internet (Link3)",
}


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"[\s\-]", "", phone.strip())
    if digits.startswith("+880"):
        digits = "0" + digits[4:]
    elif digits.startswith("880"):
        digits = "0" + digits[3:]
    return digits


def validate_phone(phone: str) -> str:
    normalized = normalize_phone(phone)
    if not BD_PHONE_RE.match(normalized):
        raise HTTPException(status_code=400, detail="Invalid Bangladeshi mobile number")
    return normalized


def validate_pin(pin: str) -> str:
    if not re.fullmatch(r"\d{4,6}", pin):
        raise HTTPException(status_code=400, detail="PIN must be 4–6 digits")
    return pin


def _money(amount: float) -> float:
    return round(float(amount), 2)


def _notify(db: Session, user_id: str, title: str, body: str) -> None:
    if user_id in SERVICE_IDS:
        return
    db.add(Notification(user_id=user_id, title=title, body=body))


def _ensure_service_account(db: Session, account_id: str, name: str, phone: str) -> User:
    row = db.get(User, account_id)
    if row:
        return row
    row = User(
        id=account_id,
        name=name,
        phone=phone,
        pin_hash=hash_pin("000000"),
        balance=0.0,
        is_active=True,
        kyc_level=KycLevel.L2_FULL.value,
    )
    db.add(row)
    db.flush()
    return row


def ensure_system_user(db: Session) -> User:
    _ensure_service_account(db, SYSTEM_ID, "PayKotha System", "00000000000")
    _ensure_service_account(db, MERCHANT_ID, "PayKotha Merchants", "00000000001")
    _ensure_service_account(db, BILLER_ID, "PayKotha Billers", "00000000002")
    _ensure_service_account(db, BANK_ID, "PayKotha Bank Bridge", "00000000003")
    db.commit()
    return db.get(User, SYSTEM_ID)  # type: ignore[return-value]


def bootstrap_admin(db: Session) -> User | None:
    """Ensure ops admin exists for maker-checker workflows."""
    settings = get_settings()
    ensure_system_user(db)
    phone = validate_phone(settings.admin_bootstrap_phone)
    existing = db.scalar(select(User).where(User.phone == phone))
    if existing:
        if not existing.is_admin:
            existing.is_admin = True
            existing.kyc_level = KycLevel.L2_FULL.value
            db.commit()
        return existing
    admin = User(
        id=f"ADM{uuid4().hex[:7].upper()}",
        name="PayKotha Ops Admin",
        phone=phone,
        pin_hash=hash_pin(settings.admin_bootstrap_pin),
        balance=0.0,
        daily_limit=1_000_000.0,
        is_admin=True,
        kyc_level=KycLevel.L2_FULL.value,
    )
    db.add(admin)
    audit(db, actor_id="SYSTEM", action="ADMIN_BOOTSTRAP", entity_type="User", entity_id=admin.id)
    db.commit()
    db.refresh(admin)
    return admin


def register_user(
    db: Session,
    name: str,
    phone: str,
    pin: str,
    opening_balance: float = 0.0,
    *,
    nid_number: str = "",
    device_id: str = "",
) -> User:
    phone = validate_phone(phone)
    pin = validate_pin(pin)
    ensure_system_user(db)

    if db.scalar(select(User).where(User.phone == phone)):
        raise HTTPException(status_code=409, detail="Phone already registered")

    kyc = KycLevel.L1_NID.value if nid_number.strip() else KycLevel.L0_BASIC.value
    limits = KYC_LIMITS[kyc]
    user = User(
        id=f"U{uuid4().hex[:8].upper()}",
        name=name.strip(),
        phone=phone,
        pin_hash=hash_pin(pin),
        balance=0.0,
        savings_balance=0.0,
        daily_limit=limits["daily"],
        kyc_level=kyc,
        nid_number=nid_number.strip(),
        device_id=device_id.strip(),
    )
    db.add(user)
    db.flush()
    audit(db, actor_id=user.id, action="USER_REGISTERED", entity_type="User", entity_id=user.id, detail=kyc)

    if opening_balance > 0:
        _post_transfer(
            db,
            sender_id=SYSTEM_ID,
            receiver_id=user.id,
            amount=_money(opening_balance),
            fee=0.0,
            txn_type=TxnType.CASH_IN,
            note="Opening balance",
            idempotency_key=f"open-{user.id}",
        )
        _notify(db, user.id, "Welcome to PayKotha", f"Account funded with ৳{opening_balance:.2f}")

    db.commit()
    db.refresh(user)
    return user


def _check_lockout(user: User) -> None:
    if user.locked_until:
        until = user.locked_until
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) < until:
            raise HTTPException(
                status_code=423,
                detail=f"Account locked until {until.isoformat()} after failed PIN attempts",
            )


def authenticate(db: Session, phone: str, pin: str, *, ip: str = "", device_id: str = "") -> User:
    phone = validate_phone(phone)
    settings = get_settings()
    rate_key = f"login:{phone}"
    attempts = redis_client.incr(rate_key, ttl=300)
    if attempts > 30:
        raise HTTPException(status_code=429, detail="Too many login attempts — try later")

    user = db.scalar(select(User).where(User.phone == phone))
    if not user or user.id in SERVICE_IDS:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account locked")
    _check_lockout(user)

    if not verify_pin(pin, user.pin_hash):
        user.failed_pin_attempts = int(user.failed_pin_attempts or 0) + 1
        if user.failed_pin_attempts >= settings.max_failed_pin_attempts:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.lockout_minutes)
            user.failed_pin_attempts = 0
            audit(db, actor_id=user.id, action="ACCOUNT_LOCKED", detail=f"ip={ip}")
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.failed_pin_attempts = 0
    user.locked_until = None
    if device_id:
        user.device_id = device_id
    audit(db, actor_id=user.id, action="LOGIN_SUCCESS", ip=ip)
    db.commit()
    return user


def change_pin(db: Session, user: User, old_pin: str, new_pin: str) -> User:
    if not verify_pin(old_pin, user.pin_hash):
        raise HTTPException(status_code=400, detail="Current PIN is incorrect")
    new_pin = validate_pin(new_pin)
    user.pin_hash = hash_pin(new_pin)
    _notify(db, user.id, "PIN updated", "Your PayKotha PIN was changed successfully.")
    audit(db, actor_id=user.id, action="PIN_CHANGED")
    db.commit()
    db.refresh(user)
    return user


def upgrade_kyc(db: Session, user: User, level: str, nid_number: str = "") -> User:
    if level not in KYC_LIMITS:
        raise HTTPException(status_code=400, detail="Invalid KYC level")
    if level in {KycLevel.L1_NID.value, KycLevel.L2_FULL.value} and not (nid_number or user.nid_number):
        raise HTTPException(status_code=400, detail="NID required for L1/L2")
    user.kyc_level = level
    if nid_number:
        user.nid_number = nid_number.strip()
    user.daily_limit = KYC_LIMITS[level]["daily"]
    audit(db, actor_id=user.id, action="KYC_UPGRADE", detail=level)
    db.commit()
    db.refresh(user)
    return user


def _ledger(
    db: Session,
    txn_id: str,
    user_id: str,
    direction: str,
    amount: float,
    balance_after: float,
    gl_account: str = "WALLET",
) -> None:
    db.add(
        LedgerEntry(
            transaction_id=txn_id,
            user_id=user_id,
            gl_account=gl_account,
            direction=direction,
            amount=amount,
            balance_after=balance_after,
        )
    )


def _find_idempotent(db: Session, key: str | None) -> Transaction | None:
    if not key:
        return None
    return db.scalar(select(Transaction).where(Transaction.idempotency_key == key))


def _daily_spent(db: Session, user_id: str) -> float:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount + Transaction.fee), 0.0)).where(
            Transaction.sender_id == user_id,
            Transaction.created_at >= start,
            Transaction.status == TxnStatus.SUCCESS.value,
        )
    )
    return float(total or 0.0)


def require_otp_if_needed(
    db: Session,
    user: User,
    amount: float,
    purpose: str,
    otp_challenge_id: str | None,
    otp_code: str | None,
) -> None:
    settings = get_settings()
    if amount < settings.require_otp_above:
        return
    if not otp_challenge_id or not otp_code:
        raise HTTPException(
            status_code=428,
            detail={
                "code": "OTP_REQUIRED",
                "message": f"OTP required for amounts ≥ ৳{settings.require_otp_above:.0f}",
                "purpose": purpose,
            },
        )
    verify_otp(db, otp_challenge_id, otp_code, user.id, purpose)


def _post_transfer(
    db: Session,
    *,
    sender_id: str,
    receiver_id: str,
    amount: float,
    fee: float,
    txn_type: TxnType,
    note: str,
    idempotency_key: str | None,
    meta: str = "",
    rail_ref: str = "",
) -> Transaction:
    existing = _find_idempotent(db, idempotency_key)
    if existing:
        return existing

    sender = db.get(User, sender_id)
    receiver = db.get(User, receiver_id)
    if not sender or not receiver:
        raise HTTPException(status_code=404, detail="Account not found")

    amount = _money(amount)
    fee = _money(fee)
    debit = _money(amount + fee)

    if sender_id not in SERVICE_IDS:
        limits = KYC_LIMITS.get(sender.kyc_level, KYC_LIMITS[KycLevel.L0_BASIC.value])
        if amount > limits["per_txn"]:
            raise HTTPException(
                status_code=400,
                detail=f"KYC {sender.kyc_level} per-txn limit ৳{limits['per_txn']:.0f}",
            )
        spent = _daily_spent(db, sender_id)
        daily_cap = min(sender.daily_limit, limits["daily"])
        if spent + debit > daily_cap:
            raise HTTPException(
                status_code=400,
                detail=f"Daily limit exceeded (limit ৳{daily_cap:.2f}, used ৳{spent:.2f})",
            )
        if sender.balance < debit:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. Available ৳{sender.balance:.2f}",
            )

    if receiver_id not in SERVICE_IDS:
        limits = KYC_LIMITS.get(receiver.kyc_level, KYC_LIMITS[KycLevel.L0_BASIC.value])
        if receiver.balance + amount > limits["wallet_max"]:
            raise HTTPException(
                status_code=400,
                detail=f"Receiver wallet would exceed KYC max ৳{limits['wallet_max']:.0f}",
            )

    txn = Transaction(
        id=f"TXN{uuid4().hex[:10].upper()}",
        sender_id=sender_id,
        receiver_id=receiver_id,
        amount=amount,
        fee=fee,
        txn_type=txn_type.value,
        status=TxnStatus.SUCCESS.value,
        note=note,
        meta=meta,
        rail_ref=rail_ref,
        idempotency_key=idempotency_key,
    )
    db.add(txn)

    if sender_id not in SERVICE_IDS:
        sender.balance = _money(sender.balance - debit)
        _ledger(db, txn.id, sender.id, "DEBIT", debit, sender.balance, "WALLET")
        if fee > 0:
            _ledger(db, txn.id, SYSTEM_ID, "CREDIT", fee, 0.0, "FEE_INCOME")
    if receiver_id not in SERVICE_IDS:
        receiver.balance = _money(receiver.balance + amount)
        _ledger(db, txn.id, receiver.id, "CREDIT", amount, receiver.balance, "WALLET")

    db.flush()
    return txn


def send_money(
    db: Session,
    sender: User,
    receiver_phone: str,
    amount: float,
    note: str = "",
    idempotency_key: str | None = None,
    *,
    otp_challenge_id: str | None = None,
    otp_code: str | None = None,
) -> Transaction:
    ensure_system_user(db)
    settings = get_settings()
    require_otp_if_needed(db, sender, amount, "TRANSFER", otp_challenge_id, otp_code)
    receiver_phone = validate_phone(receiver_phone)
    receiver = db.scalar(select(User).where(User.phone == receiver_phone))
    if not receiver or receiver.id in SERVICE_IDS:
        raise HTTPException(status_code=404, detail="Receiver not found")
    if receiver.id == sender.id:
        raise HTTPException(status_code=400, detail="Cannot send money to yourself")

    fee = _money(amount * settings.send_fee_rate)
    txn = _post_transfer(
        db,
        sender_id=sender.id,
        receiver_id=receiver.id,
        amount=amount,
        fee=fee,
        txn_type=TxnType.SEND,
        note=note or "Send money",
        idempotency_key=idempotency_key,
    )
    _notify(db, sender.id, "Money sent", f"You sent ৳{amount:.2f} to {receiver.phone}")
    _notify(db, receiver.id, "Money received", f"You received ৳{amount:.2f} from {sender.phone}")
    audit(db, actor_id=sender.id, action="SEND", entity_type="Transaction", entity_id=txn.id)
    db.commit()
    _live([sender.id, receiver.id], "TRANSFER", amount=amount, txn_id=txn.id)
    db.refresh(txn)
    return txn


def cash_in(db: Session, user: User, amount: float, note: str = "", idempotency_key: str | None = None) -> Transaction:
    ensure_system_user(db)
    txn = _post_transfer(
        db,
        sender_id=SYSTEM_ID,
        receiver_id=user.id,
        amount=amount,
        fee=0.0,
        txn_type=TxnType.CASH_IN,
        note=note or "Cash in via agent",
        idempotency_key=idempotency_key,
    )
    _notify(db, user.id, "Cash in", f"৳{amount:.2f} added to wallet")
    db.commit()
    _live([user.id], "CASH_IN", amount=amount)
    db.refresh(txn)
    return txn


def cash_out(
    db: Session,
    user: User,
    amount: float,
    note: str = "",
    idempotency_key: str | None = None,
    *,
    otp_challenge_id: str | None = None,
    otp_code: str | None = None,
) -> Transaction:
    ensure_system_user(db)
    settings = get_settings()
    require_otp_if_needed(db, user, amount, "CASH_OUT", otp_challenge_id, otp_code)
    fee = _money(amount * settings.cash_out_fee_rate)
    txn = _post_transfer(
        db,
        sender_id=user.id,
        receiver_id=SYSTEM_ID,
        amount=amount,
        fee=fee,
        txn_type=TxnType.CASH_OUT,
        note=note or "Cash out via agent",
        idempotency_key=idempotency_key,
    )
    _notify(db, user.id, "Cash out", f"৳{amount:.2f} withdrawn (fee ৳{fee:.2f})")
    audit(db, actor_id=user.id, action="CASH_OUT", entity_id=txn.id)
    db.commit()
    _live([user.id], "CASH_OUT", amount=amount)
    db.refresh(txn)
    return txn


def mobile_recharge(
    db: Session,
    user: User,
    operator: str,
    mobile: str,
    amount: float,
    idempotency_key: str | None = None,
) -> Transaction:
    ensure_system_user(db)
    if operator not in OPERATORS:
        raise HTTPException(status_code=400, detail=f"Operator must be one of: {', '.join(sorted(OPERATORS))}")
    mobile = validate_phone(mobile)
    if amount < 20 or amount > 1000:
        raise HTTPException(status_code=400, detail="Recharge amount must be between ৳20 and ৳1000")
    meta = json.dumps({"operator": operator, "mobile": mobile})
    txn = _post_transfer(
        db,
        sender_id=user.id,
        receiver_id=MERCHANT_ID,
        amount=amount,
        fee=0.0,
        txn_type=TxnType.RECHARGE,
        note=f"{operator} recharge to {mobile}",
        idempotency_key=idempotency_key,
        meta=meta,
    )
    _notify(db, user.id, "Recharge successful", f"{operator} ৳{amount:.2f} → {mobile}")
    db.commit()
    _live([user.id], "RECHARGE", amount=amount)
    db.refresh(txn)
    return txn


def bill_pay(
    db: Session,
    user: User,
    biller_code: str,
    account_no: str,
    amount: float,
    idempotency_key: str | None = None,
) -> Transaction:
    ensure_system_user(db)
    if biller_code not in BILLERS:
        raise HTTPException(status_code=400, detail=f"Unknown biller. Use: {', '.join(BILLERS)}")
    if not account_no.strip():
        raise HTTPException(status_code=400, detail="Account / consumer number required")
    fee = 5.0 if amount >= 100 else 0.0
    meta = json.dumps({"biller": biller_code, "account_no": account_no.strip()})
    txn = _post_transfer(
        db,
        sender_id=user.id,
        receiver_id=BILLER_ID,
        amount=amount,
        fee=fee,
        txn_type=TxnType.BILL_PAY,
        note=f"{BILLERS[biller_code]} · A/C {account_no.strip()}",
        idempotency_key=idempotency_key,
        meta=meta,
    )
    _notify(db, user.id, "Bill paid", f"{BILLERS[biller_code]} ৳{amount:.2f}")
    db.commit()
    _live([user.id], "BILL_PAY", amount=amount)
    db.refresh(txn)
    return txn


def merchant_pay(
    db: Session,
    user: User,
    merchant_code: str,
    amount: float,
    note: str = "",
    idempotency_key: str | None = None,
) -> Transaction:
    ensure_system_user(db)
    code = merchant_code.strip().upper()
    if len(code) < 4:
        raise HTTPException(status_code=400, detail="Invalid merchant / QR code")
    fee = _money(amount * 0.01)
    meta = json.dumps({"merchant_code": code, "channel": "QR"})
    txn = _post_transfer(
        db,
        sender_id=user.id,
        receiver_id=MERCHANT_ID,
        amount=amount,
        fee=fee,
        txn_type=TxnType.MERCHANT,
        note=note or f"Merchant pay · {code}",
        idempotency_key=idempotency_key,
        meta=meta,
    )
    _notify(db, user.id, "Merchant payment", f"Paid ৳{amount:.2f} to {code}")
    db.commit()
    _live([user.id], "MERCHANT", amount=amount)
    db.refresh(txn)
    return txn


def bank_transfer_out(
    db: Session,
    user: User,
    bank_account: str,
    amount: float,
    idempotency_key: str | None = None,
    *,
    otp_challenge_id: str | None = None,
    otp_code: str | None = None,
) -> Transaction:
    ensure_system_user(db)
    require_otp_if_needed(db, user, amount, "TRANSFER", otp_challenge_id, otp_code)
    acc = bank_account.strip()
    if len(acc) < 8:
        raise HTTPException(status_code=400, detail="Enter a valid bank account / IBAN-like number")
    rail = get_rail()
    result = rail.transfer(
        from_account=user.phone,
        to_account=acc,
        amount=amount,
        narrative="Wallet to bank",
    )
    if not result.success:
        raise HTTPException(status_code=502, detail=f"Payment rail declined: {result.message}")
    fee = 10.0
    meta = json.dumps({"bank_account": acc, "rail": get_settings().rail_mode})
    txn = _post_transfer(
        db,
        sender_id=user.id,
        receiver_id=BANK_ID,
        amount=amount,
        fee=fee,
        txn_type=TxnType.BANK_OUT,
        note=f"Transfer to bank ···{acc[-4:]}",
        idempotency_key=idempotency_key,
        meta=meta,
        rail_ref=result.rail_ref,
    )
    user.bank_account = acc
    _notify(db, user.id, "Bank transfer", f"৳{amount:.2f} sent · ref {result.rail_ref}")
    audit(db, actor_id=user.id, action="BANK_OUT", entity_id=txn.id, detail=result.rail_ref)
    db.commit()
    _live([user.id], "BANK_OUT", amount=amount)
    db.refresh(txn)
    return txn


def add_money_from_bank(
    db: Session,
    user: User,
    amount: float,
    bank_account: str = "",
    idempotency_key: str | None = None,
) -> Transaction:
    ensure_system_user(db)
    rail = get_rail()
    result = rail.transfer(
        from_account=bank_account or user.bank_account or "LINKED-BANK",
        to_account=user.phone,
        amount=amount,
        narrative="Bank to wallet",
    )
    if not result.success:
        raise HTTPException(status_code=502, detail=f"Payment rail declined: {result.message}")
    meta = json.dumps({"bank_account": bank_account or user.bank_account or "LINKED-BANK", "rail": get_settings().rail_mode})
    txn = _post_transfer(
        db,
        sender_id=BANK_ID,
        receiver_id=user.id,
        amount=amount,
        fee=0.0,
        txn_type=TxnType.BANK_IN,
        note="Add money from bank",
        idempotency_key=idempotency_key,
        meta=meta,
        rail_ref=result.rail_ref,
    )
    _notify(db, user.id, "Add money", f"৳{amount:.2f} added · ref {result.rail_ref}")
    db.commit()
    _live([user.id], "BANK_IN", amount=amount)
    db.refresh(txn)
    return txn


def create_money_request(db: Session, user: User, payer_phone: str, amount: float, note: str = "") -> MoneyRequest:
    payer_phone = validate_phone(payer_phone)
    if payer_phone == user.phone:
        raise HTTPException(status_code=400, detail="Cannot request money from yourself")
    req = MoneyRequest(
        id=f"REQ{uuid4().hex[:8].upper()}",
        requester_id=user.id,
        payer_phone=payer_phone,
        amount=_money(amount),
        note=note or "Money request",
        status=RequestStatus.PENDING.value,
    )
    db.add(req)
    payer = db.scalar(select(User).where(User.phone == payer_phone))
    if payer:
        _notify(db, payer.id, "Money request", f"{user.name} requested ৳{amount:.2f}")
    db.commit()
    targets = [user.id] + ([payer.id] if payer else [])
    _live(targets, "MONEY_REQUEST", amount=amount, request_id=req.id)
    db.refresh(req)
    return req


def list_money_requests(db: Session, user: User) -> list[MoneyRequest]:
    incoming = list(
        db.scalars(
            select(MoneyRequest)
            .where(MoneyRequest.payer_phone == user.phone)
            .order_by(MoneyRequest.created_at.desc())
        )
    )
    outgoing = list(
        db.scalars(
            select(MoneyRequest)
            .where(MoneyRequest.requester_id == user.id)
            .order_by(MoneyRequest.created_at.desc())
        )
    )
    seen = {}
    for r in incoming + outgoing:
        seen[r.id] = r
    return sorted(seen.values(), key=lambda r: r.created_at or datetime.min, reverse=True)


def pay_money_request(db: Session, user: User, request_id: str, idempotency_key: str | None = None) -> Transaction:
    req = db.get(MoneyRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.payer_phone != user.phone:
        raise HTTPException(status_code=403, detail="Only the payer can fulfill this request")
    if req.status != RequestStatus.PENDING.value:
        raise HTTPException(status_code=400, detail=f"Request is {req.status}")
    requester = db.get(User, req.requester_id)
    if not requester:
        raise HTTPException(status_code=404, detail="Requester missing")

    ensure_system_user(db)
    settings = get_settings()
    fee = _money(req.amount * settings.send_fee_rate)
    txn = _post_transfer(
        db,
        sender_id=user.id,
        receiver_id=requester.id,
        amount=req.amount,
        fee=fee,
        txn_type=TxnType.REQUEST_PAY,
        note=f"Paid request {req.id}",
        idempotency_key=idempotency_key or f"pay-{req.id}",
    )
    req.status = RequestStatus.PAID.value
    _notify(db, user.id, "Request paid", f"You paid ৳{req.amount:.2f}")
    _notify(db, requester.id, "Request received", f"{user.name} paid your request")
    db.commit()
    _live([user.id, requester.id], "REQUEST_PAY", amount=req.amount, request_id=req.id)
    db.refresh(txn)
    return txn


def cancel_money_request(db: Session, user: User, request_id: str) -> MoneyRequest:
    req = db.get(MoneyRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.requester_id != user.id:
        raise HTTPException(status_code=403, detail="Only requester can cancel")
    if req.status != RequestStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Only pending requests can be cancelled")
    req.status = RequestStatus.CANCELLED.value
    db.commit()
    _live([user.id], "REQUEST_CANCEL", request_id=req.id)
    db.refresh(req)
    return req


def savings_deposit(db: Session, user: User, amount: float, idempotency_key: str | None = None) -> Transaction:
    ensure_system_user(db)
    amount = _money(amount)
    if user.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    txn = _post_transfer(
        db,
        sender_id=user.id,
        receiver_id=SYSTEM_ID,
        amount=amount,
        fee=0.0,
        txn_type=TxnType.SAVINGS_IN,
        note="Move to Savings Pot",
        idempotency_key=idempotency_key,
        meta=json.dumps({"pot": "SAVINGS"}),
    )
    user.savings_balance = _money(user.savings_balance + amount)
    _notify(db, user.id, "Savings deposit", f"৳{amount:.2f} moved to Savings Pot")
    db.commit()
    _live([user.id], "SAVINGS_IN", amount=amount)
    db.refresh(txn)
    return txn


def savings_withdraw(db: Session, user: User, amount: float, idempotency_key: str | None = None) -> Transaction:
    ensure_system_user(db)
    amount = _money(amount)
    if user.savings_balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient savings balance")
    user.savings_balance = _money(user.savings_balance - amount)
    txn = _post_transfer(
        db,
        sender_id=SYSTEM_ID,
        receiver_id=user.id,
        amount=amount,
        fee=0.0,
        txn_type=TxnType.SAVINGS_OUT,
        note="Withdraw from Savings Pot",
        idempotency_key=idempotency_key,
        meta=json.dumps({"pot": "SAVINGS"}),
    )
    _notify(db, user.id, "Savings withdraw", f"৳{amount:.2f} returned to wallet")
    db.commit()
    _live([user.id], "SAVINGS_OUT", amount=amount)
    db.refresh(txn)
    return txn


def donate(
    db: Session,
    user: User,
    cause: str,
    amount: float,
    idempotency_key: str | None = None,
) -> Transaction:
    ensure_system_user(db)
    cause = cause.strip() or "General charity"
    txn = _post_transfer(
        db,
        sender_id=user.id,
        receiver_id=MERCHANT_ID,
        amount=amount,
        fee=0.0,
        txn_type=TxnType.DONATION,
        note=f"Donation · {cause}",
        idempotency_key=idempotency_key,
        meta=json.dumps({"cause": cause}),
    )
    _notify(db, user.id, "Donation sent", f"Thank you for donating ৳{amount:.2f}")
    db.commit()
    _live([user.id], "DONATION", amount=amount)
    db.refresh(txn)
    return txn


def add_favorite(db: Session, user: User, label: str, phone: str, kind: str = "CONTACT") -> Favorite:
    phone = validate_phone(phone) if kind == "CONTACT" else phone.strip()
    fav = Favorite(user_id=user.id, label=label.strip(), phone=phone, kind=kind.upper())
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


def list_favorites(db: Session, user: User) -> list[Favorite]:
    return list(db.scalars(select(Favorite).where(Favorite.user_id == user.id).order_by(Favorite.id.desc())))


def delete_favorite(db: Session, user: User, fav_id: int) -> None:
    fav = db.get(Favorite, fav_id)
    if not fav or fav.user_id != user.id:
        raise HTTPException(status_code=404, detail="Favorite not found")
    db.delete(fav)
    db.commit()


def list_notifications(db: Session, user: User, limit: int = 30) -> list[Notification]:
    return list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
    )


def mark_notifications_read(db: Session, user: User) -> int:
    rows = list(db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False))))
    for n in rows:
        n.is_read = True
    db.commit()
    return len(rows)


def list_transactions(db: Session, user: User, limit: int = 80) -> list[Transaction]:
    stmt = (
        select(Transaction)
        .where(or_(Transaction.sender_id == user.id, Transaction.receiver_id == user.id))
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def catalog() -> dict:
    settings = get_settings()
    return {
        "operators": sorted(OPERATORS),
        "billers": BILLERS,
        "kyc_limits": KYC_LIMITS,
        "require_otp_above": settings.require_otp_above,
        "rail_mode": settings.rail_mode,
        "features": [
            "send",
            "cash_in",
            "cash_out",
            "recharge",
            "bill_pay",
            "merchant_qr",
            "bank_transfer",
            "add_money_bank",
            "request_money",
            "savings_pot",
            "donation",
            "favorites",
            "notifications",
            "change_pin",
            "excel_export",
            "otp_high_value",
            "kyc_tiers",
            "maker_checker_reversal",
            "eod_settlement",
            "reconciliation",
            "audit_trail",
            "payment_rails",
        ],
    }


def platform_stats(db: Session) -> dict:
    users = db.scalar(select(func.count()).select_from(User).where(User.id.notin_(list(SERVICE_IDS)))) or 0
    txns = db.scalar(select(func.count()).select_from(Transaction)) or 0
    volume = db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0.0))) or 0.0
    return {"users": int(users), "transactions": int(txns), "total_volume": float(volume)}
