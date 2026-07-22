from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


class TransactionType(str, Enum):
    SEND = "SEND"
    RECEIVE = "RECEIVE"
    CASH_IN = "CASH_IN"
    CASH_OUT = "CASH_OUT"
    FEE = "FEE"


@dataclass
class Transaction:
    """Immutable money-movement record linking sender and receiver."""

    sender_id: str
    receiver_id: str
    amount: float
    transaction_type: TransactionType = TransactionType.SEND
    transaction_id: str = field(default_factory=lambda: f"TXN-{uuid4().hex[:10].upper()}")
    date: datetime = field(default_factory=datetime.now)
    note: str = ""
    fee: float = 0.0
    status: str = "SUCCESS"

    # Optional live object refs (not persisted)
    sender: Optional[object] = field(default=None, repr=False)
    receiver: Optional[object] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.amount = round(float(self.amount), 2)
        self.fee = round(float(self.fee), 2)
        if isinstance(self.transaction_type, str):
            self.transaction_type = TransactionType(self.transaction_type)
        if isinstance(self.date, str):
            self.date = datetime.fromisoformat(self.date)

    def to_dict(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "amount": self.amount,
            "fee": self.fee,
            "transaction_type": self.transaction_type.value,
            "date": self.date.isoformat(timespec="seconds"),
            "note": self.note,
            "status": self.status,
        }

    def display(self) -> str:
        when = self.date.strftime("%Y-%m-%d %H:%M")
        return (
            f"{self.transaction_id} | {self.transaction_type.value:8} | "
            f"{self.sender_id} → {self.receiver_id} | ৳{self.amount:.2f} "
            f"(fee ৳{self.fee:.2f}) | {when} | {self.status}"
        )
