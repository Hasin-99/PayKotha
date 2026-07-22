from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .transaction import Transaction
from .wallet import Wallet


@dataclass
class User:
    """Registered mobile-wallet account (bKash-style user)."""

    user_id: str
    name: str
    phone_number: str
    pin_hash: str
    wallet: Wallet = field(default_factory=Wallet)
    created_at: str = ""
    is_active: bool = True

    def display_details(self) -> str:
        return (
            f"User ID : {self.user_id}\n"
            f"Name    : {self.name}\n"
            f"Phone   : {self.phone_number}\n"
            f"Balance : ৳{self.wallet.check_balance():.2f}\n"
            f"Status  : {'Active' if self.is_active else 'Locked'}"
        )

    def receive_money(self, amount: float) -> float:
        """Credit this user's wallet (receive / cash-in destination)."""
        return self.wallet.add_funds(amount)

    def send_money(self, amount: float) -> float:
        """Debit this user's wallet when sending / cashing out."""
        return self.wallet.withdraw_funds(amount)

    def check_balance(self) -> float:
        return self.wallet.check_balance()

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "phone_number": self.phone_number,
            "pin_hash": self.pin_hash,
            "balance": self.wallet.balance,
            "created_at": self.created_at,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            user_id=str(data["user_id"]),
            name=str(data["name"]),
            phone_number=str(data["phone_number"]),
            pin_hash=str(data["pin_hash"]),
            wallet=Wallet(balance=float(data.get("balance", 0))),
            created_at=str(data.get("created_at", "")),
            is_active=bool(data.get("is_active", True)),
        )
