from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Wallet:
    """Digital wallet holding the user's current balance."""

    balance: float = 0.0

    def __post_init__(self) -> None:
        self.balance = float(self.balance)
        if self.balance < 0:
            raise ValueError("Wallet balance cannot be negative")

    def add_funds(self, amount: float) -> float:
        """Deposit / cash-in / receive money."""
        amount = self._validate_amount(amount)
        self.balance = round(self.balance + amount, 2)
        return self.balance

    def withdraw_funds(self, amount: float) -> float:
        """Send money / cash-out — fails if insufficient."""
        amount = self._validate_amount(amount)
        if amount > self.balance:
            raise ValueError(
                f"Insufficient balance. Available: ৳{self.balance:.2f}, requested: ৳{amount:.2f}"
            )
        self.balance = round(self.balance - amount, 2)
        return self.balance

    def check_balance(self) -> float:
        return round(self.balance, 2)

    @staticmethod
    def _validate_amount(amount: float) -> float:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        if round(amount, 2) != amount and abs(amount - round(amount, 2)) > 1e-9:
            amount = round(amount, 2)
        return round(amount, 2)

    def to_dict(self) -> dict:
        return {"balance": self.balance}
