from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str
    pin: str = Field(min_length=4, max_length=6)
    opening_balance: float = Field(default=0, ge=0)
    nid_number: str = ""
    device_id: str = ""


class LoginRequest(BaseModel):
    phone: str
    pin: str
    device_id: str = ""


class ChangePinRequest(BaseModel):
    old_pin: str
    new_pin: str = Field(min_length=4, max_length=6)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str = ""
    token_type: str = "bearer"
    expires_in: int = 1800


class KycUpgradeRequest(BaseModel):
    level: str = Field(description="L0_BASIC | L1_NID | L2_FULL")
    nid_number: str = ""


class OtpIssueRequest(BaseModel):
    purpose: str = Field(description="TRANSFER | CASH_OUT | LOGIN")


class OtpVerifyFields(BaseModel):
    otp_challenge_id: Optional[str] = None
    otp_code: Optional[str] = None


class UserPublic(BaseModel):
    id: str
    name: str
    phone: str
    balance: float
    savings_balance: float = 0
    daily_limit: float = 25000
    bank_account: str = ""
    is_active: bool
    is_admin: bool = False
    kyc_level: str = "L0_BASIC"
    created_at: datetime

    model_config = {"from_attributes": True}


class TransferRequest(OtpVerifyFields):
    receiver_phone: str
    amount: float = Field(gt=0)
    note: str = ""
    idempotency_key: Optional[str] = None


class AmountRequest(OtpVerifyFields):
    amount: float = Field(gt=0)
    note: str = ""
    idempotency_key: Optional[str] = None


class RechargeRequest(BaseModel):
    operator: str
    mobile: str
    amount: float = Field(gt=0)
    idempotency_key: Optional[str] = None


class BillPayRequest(BaseModel):
    biller_code: str
    account_no: str
    amount: float = Field(gt=0)
    idempotency_key: Optional[str] = None


class MerchantPayRequest(BaseModel):
    merchant_code: str
    amount: float = Field(gt=0)
    note: str = ""
    idempotency_key: Optional[str] = None


class BankOutRequest(OtpVerifyFields):
    bank_account: str
    amount: float = Field(gt=0)
    idempotency_key: Optional[str] = None


class BankInRequest(BaseModel):
    amount: float = Field(gt=0)
    bank_account: str = ""
    idempotency_key: Optional[str] = None


class RequestMoneyCreate(BaseModel):
    payer_phone: str
    amount: float = Field(gt=0)
    note: str = ""


class DonationRequest(BaseModel):
    cause: str = "General charity"
    amount: float = Field(gt=0)
    idempotency_key: Optional[str] = None


class FavoriteIn(BaseModel):
    label: str
    phone: str
    kind: str = "CONTACT"


class FavoriteOut(BaseModel):
    id: int
    label: str
    phone: str
    kind: str

    model_config = {"from_attributes": True}


class MoneyRequestOut(BaseModel):
    id: str
    requester_id: str
    payer_phone: str
    amount: float
    note: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationOut(BaseModel):
    id: int
    title: str
    body: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionOut(BaseModel):
    id: str
    sender_id: str
    receiver_id: str
    amount: float
    fee: float
    txn_type: str
    status: str
    note: str
    meta: str = ""
    rail_ref: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class PlatformStats(BaseModel):
    users: int
    transactions: int
    total_volume: float


class ReversalCreate(BaseModel):
    transaction_id: str
    reason: str = Field(min_length=5)


class ReversalDecide(BaseModel):
    approve: bool


class ReversalOut(BaseModel):
    id: str
    transaction_id: str
    maker_id: str
    checker_id: Optional[str] = None
    reason: str
    status: str
    created_at: datetime
    decided_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SettlementOut(BaseModel):
    id: str
    status: str
    txn_count: int
    gross_amount: float
    fee_amount: float
    net_amount: float
    rail_ref: str
    created_at: datetime
    closed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AuditOut(BaseModel):
    id: int
    actor_id: str
    action: str
    entity_type: str
    entity_id: str
    detail: str
    ip: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OtpIssueResponse(BaseModel):
    challenge_id: str
    expires_in: int
    purpose: str
    delivery: str
    sandbox_code: Optional[str] = None
