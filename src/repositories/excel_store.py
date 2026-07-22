from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd

from src.models import Transaction, TransactionType, User, Wallet


class ExcelStore:
    """Persistence layer — users & transactions in Excel (pandas + openpyxl)."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.users_path = self.data_dir / "users.xlsx"
        self.transactions_path = self.data_dir / "transactions.xlsx"

    def load(self) -> Tuple[List[User], List[Transaction]]:
        users = self._load_users()
        transactions = self._load_transactions()
        return users, transactions

    def save(self, users: List[User], transactions: List[Transaction]) -> None:
        self._save_users(users)
        self._save_transactions(transactions)

    def _load_users(self) -> List[User]:
        if not self.users_path.exists():
            return []
        df = pd.read_excel(self.users_path, dtype=str)
        if df.empty:
            return []
        users: List[User] = []
        for _, row in df.iterrows():
            users.append(
                User(
                    user_id=str(row["user_id"]),
                    name=str(row["name"]),
                    phone_number=str(row["phone_number"]),
                    pin_hash=str(row["pin_hash"]),
                    wallet=Wallet(balance=float(row.get("balance", 0) or 0)),
                    created_at=str(row.get("created_at", "") or ""),
                    is_active=str(row.get("is_active", "True")).lower() in {"true", "1", "yes"},
                )
            )
        return users

    def _save_users(self, users: List[User]) -> None:
        rows = [u.to_dict() for u in users]
        df = pd.DataFrame(
            rows,
            columns=[
                "user_id",
                "name",
                "phone_number",
                "pin_hash",
                "balance",
                "created_at",
                "is_active",
            ],
        )
        df.to_excel(self.users_path, index=False)

    def _load_transactions(self) -> List[Transaction]:
        if not self.transactions_path.exists():
            return []
        df = pd.read_excel(self.transactions_path, dtype=str)
        if df.empty:
            return []
        txns: List[Transaction] = []
        for _, row in df.iterrows():
            txns.append(
                Transaction(
                    transaction_id=str(row["transaction_id"]),
                    sender_id=str(row["sender_id"]),
                    receiver_id=str(row["receiver_id"]),
                    amount=float(row["amount"]),
                    fee=float(row.get("fee", 0) or 0),
                    transaction_type=TransactionType(str(row.get("transaction_type", "SEND"))),
                    date=str(row["date"]),
                    note=str(row.get("note", "") or ""),
                    status=str(row.get("status", "SUCCESS") or "SUCCESS"),
                )
            )
        return txns

    def _save_transactions(self, transactions: List[Transaction]) -> None:
        rows = [t.to_dict() for t in transactions]
        df = pd.DataFrame(
            rows,
            columns=[
                "transaction_id",
                "sender_id",
                "receiver_id",
                "amount",
                "fee",
                "transaction_type",
                "date",
                "note",
                "status",
            ],
        )
        df.to_excel(self.transactions_path, index=False)
