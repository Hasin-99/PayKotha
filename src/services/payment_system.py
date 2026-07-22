from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from src.models import Transaction, TransactionType, User, Wallet
from src.repositories.excel_store import ExcelStore
from src.utils.security import hash_pin, verify_pin
from src.utils.validators import validate_name, validate_phone, validate_pin


class PaymentSystem:
    """
    Core domain service — registration, auth, P2P transfer,
    cash-in / cash-out, history, Excel load/save.
    """

    SYSTEM_ID = "SYSTEM"
    SEND_FEE_RATE = 0.0  # set > 0 for industry-style fee simulation
    CASH_OUT_FEE_RATE = 0.018  # ~1.8% like typical agent cash-out

    def __init__(self, store: ExcelStore) -> None:
        self.store = store
        self.users: Dict[str, User] = {}
        self.transactions: List[Transaction] = []
        self._phone_index: Dict[str, str] = {}

    # ------------------------------------------------------------------ load/save
    def load(self) -> None:
        users, txns = self.store.load()
        self.users = {u.user_id: u for u in users}
        self.transactions = txns
        self._phone_index = {u.phone_number: u.user_id for u in users}

    def save(self) -> None:
        self.store.save(list(self.users.values()), self.transactions)

    # ------------------------------------------------------------------ helpers
    def get_user(self, user_id: str) -> User:
        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User '{user_id}' not found")
        if not user.is_active:
            raise ValueError("Account is locked")
        return user

    def find_by_phone(self, phone: str) -> User:
        phone = validate_phone(phone)
        user_id = self._phone_index.get(phone)
        if not user_id:
            raise ValueError("No account found for this phone number")
        return self.get_user(user_id)

    def authenticate(self, phone: str, pin: str) -> User:
        user = self.find_by_phone(phone)
        if not verify_pin(pin, user.pin_hash):
            raise ValueError("Incorrect PIN")
        return user

    # ------------------------------------------------------------------ register
    def register_user(self, name: str, phone: str, pin: str, opening_balance: float = 0.0) -> User:
        name = validate_name(name)
        phone = validate_phone(phone)
        pin = validate_pin(pin)

        if phone in self._phone_index:
            raise ValueError("Phone number already registered")

        user_id = f"U{uuid4().hex[:6].upper()}"
        user = User(
            user_id=user_id,
            name=name,
            phone_number=phone,
            pin_hash=hash_pin(pin),
            wallet=Wallet(balance=float(opening_balance)),
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self.users[user_id] = user
        self._phone_index[phone] = user_id

        if opening_balance > 0:
            self.transactions.append(
                Transaction(
                    sender_id=self.SYSTEM_ID,
                    receiver_id=user_id,
                    amount=opening_balance,
                    transaction_type=TransactionType.CASH_IN,
                    note="Opening balance",
                    sender=None,
                    receiver=user,
                )
            )
        return user

    # ------------------------------------------------------------------ money ops
    def cash_in(self, user: User, amount: float, note: str = "Cash in via agent") -> Transaction:
        user.receive_money(amount)
        txn = Transaction(
            sender_id=self.SYSTEM_ID,
            receiver_id=user.user_id,
            amount=amount,
            transaction_type=TransactionType.CASH_IN,
            note=note,
            receiver=user,
        )
        self.transactions.append(txn)
        return txn

    def cash_out(self, user: User, amount: float, note: str = "Cash out via agent") -> Transaction:
        fee = round(amount * self.CASH_OUT_FEE_RATE, 2)
        total = round(amount + fee, 2)
        user.send_money(total)
        txn = Transaction(
            sender_id=user.user_id,
            receiver_id=self.SYSTEM_ID,
            amount=amount,
            fee=fee,
            transaction_type=TransactionType.CASH_OUT,
            note=note,
            sender=user,
        )
        self.transactions.append(txn)
        return txn

    def send_money(
        self,
        sender: User,
        receiver_phone: str,
        amount: float,
        note: str = "",
    ) -> Transaction:
        receiver = self.find_by_phone(receiver_phone)
        if receiver.user_id == sender.user_id:
            raise ValueError("Cannot send money to yourself")

        fee = round(amount * self.SEND_FEE_RATE, 2)
        total_debit = round(amount + fee, 2)

        sender.send_money(total_debit)
        receiver.receive_money(amount)

        txn = Transaction(
            sender_id=sender.user_id,
            receiver_id=receiver.user_id,
            amount=amount,
            fee=fee,
            transaction_type=TransactionType.SEND,
            note=note or "P2P transfer",
            sender=sender,
            receiver=receiver,
        )
        self.transactions.append(txn)
        return txn

    def receive_money(
        self,
        receiver: User,
        sender_phone: str,
        amount: float,
        note: str = "",
    ) -> Transaction:
        """
        Spec menu item 'Receive Money' — pull from another user's wallet
        (request-style receive). Requires sender phone + amount.
        """
        sender = self.find_by_phone(sender_phone)
        return self.send_money(sender, receiver.phone_number, amount, note or "Received funds")

    def history_for(self, user: User, limit: int = 20) -> List[Transaction]:
        rows = [
            t
            for t in self.transactions
            if t.sender_id == user.user_id or t.receiver_id == user.user_id
        ]
        rows.sort(key=lambda t: t.date, reverse=True)
        return rows[:limit]

    def stats(self) -> dict:
        return {
            "users": len(self.users),
            "transactions": len(self.transactions),
            "total_volume": round(sum(t.amount for t in self.transactions), 2),
        }
