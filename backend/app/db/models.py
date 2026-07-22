from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class KycLevel(str, enum.Enum):
    L0_BASIC = "L0_BASIC"
    L1_NID = "L1_NID"
    L2_FULL = "L2_FULL"


class TxnType(str, enum.Enum):
    SEND = "SEND"
    CASH_IN = "CASH_IN"
    CASH_OUT = "CASH_OUT"
    RECHARGE = "RECHARGE"
    BILL_PAY = "BILL_PAY"
    MERCHANT = "MERCHANT"
    BANK_OUT = "BANK_OUT"
    BANK_IN = "BANK_IN"
    REQUEST_PAY = "REQUEST_PAY"
    DONATION = "DONATION"
    SAVINGS_IN = "SAVINGS_IN"
    SAVINGS_OUT = "SAVINGS_OUT"
    REVERSAL = "REVERSAL"
    SETTLEMENT = "SETTLEMENT"


class TxnStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"
    REVERSED = "REVERSED"


class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    DECLINED = "DECLINED"


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    savings_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    daily_limit: Mapped[float] = mapped_column(Float, default=25000.0, nullable=False)
    bank_account: Mapped[str] = mapped_column(String(34), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    kyc_level: Mapped[str] = mapped_column(String(20), default=KycLevel.L0_BASIC.value)
    nid_number: Mapped[str] = mapped_column(String(30), default="")
    failed_pin_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    device_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sent_transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="sender", foreign_keys="Transaction.sender_id"
    )
    received_transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="receiver", foreign_keys="Transaction.receiver_id"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sender_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False)
    receiver_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    txn_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=TxnStatus.SUCCESS.value)
    note: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[str] = mapped_column(Text, default="")
    rail_ref: Mapped[str] = mapped_column(String(64), default="")  # external rail reference
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sender: Mapped[User] = relationship(foreign_keys=[sender_id], back_populates="sent_transactions")
    receiver: Mapped[User] = relationship(foreign_keys=[receiver_id], back_populates="received_transactions")


class LedgerEntry(Base):
    """Immutable double-entry line."""

    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(32), ForeignKey("transactions.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), index=True)
    gl_account: Mapped[str] = mapped_column(String(64), default="WALLET")  # WALLET / FEE / SETTLEMENT / SUSPENSE
    direction: Mapped[str] = mapped_column(String(8))  # DEBIT / CREDIT
    amount: Mapped[float] = mapped_column(Float)
    balance_after: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MoneyRequest(Base):
    __tablename__ = "money_requests"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    requester_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), index=True)
    payer_phone: Mapped[str] = mapped_column(String(20), index=True)
    amount: Mapped[float] = mapped_column(Float)
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default=RequestStatus.PENDING.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), index=True)
    label: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(20), default="CONTACT")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_id: Mapped[str] = mapped_column(String(32), default="SYSTEM", index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OtpChallenge(Base):
    __tablename__ = "otp_challenges"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(40))  # LOGIN / TRANSFER / CASH_OUT
    code_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReversalRequest(Base):
    """Maker-checker reversal workflow."""

    __tablename__ = "reversal_requests"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(32), ForeignKey("transactions.id"), index=True)
    maker_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"))
    checker_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=ApprovalStatus.PENDING.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SettlementBatch(Base):
    __tablename__ = "settlement_batches"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    txn_count: Mapped[int] = mapped_column(Integer, default=0)
    gross_amount: Mapped[float] = mapped_column(Float, default=0.0)
    fee_amount: Mapped[float] = mapped_column(Float, default=0.0)
    net_amount: Mapped[float] = mapped_column(Float, default=0.0)
    rail_ref: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_idem"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    key: Mapped[str] = mapped_column(String(64))
    response_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
