from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.models import Transaction, User
from backend.app.services.wallet_service import BANK_ID, BILLER_ID, MERCHANT_ID, SYSTEM_ID


SERVICE_IDS = {SYSTEM_ID, MERCHANT_ID, BILLER_ID, BANK_ID}


def export_to_excel(db: Session) -> dict[str, str]:
    """Course requirement bridge — dump SQL state to Excel workbooks."""
    settings = get_settings()
    out = Path(settings.excel_export_dir)
    out.mkdir(parents=True, exist_ok=True)

    users = db.scalars(select(User).where(User.id.not_in(list(SERVICE_IDS)))).all()
    txns = db.scalars(select(Transaction).order_by(Transaction.created_at.desc())).all()

    users_path = out / "users.xlsx"
    txns_path = out / "transactions.xlsx"

    pd.DataFrame(
        [
            {
                "user_id": u.id,
                "name": u.name,
                "phone_number": u.phone,
                "balance": u.balance,
                "savings_balance": u.savings_balance,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else "",
            }
            for u in users
        ]
    ).to_excel(users_path, index=False)

    pd.DataFrame(
        [
            {
                "transaction_id": t.id,
                "sender_id": t.sender_id,
                "receiver_id": t.receiver_id,
                "amount": t.amount,
                "fee": t.fee,
                "transaction_type": t.txn_type if isinstance(t.txn_type, str) else getattr(t.txn_type, "value", t.txn_type),
                "status": t.status if isinstance(t.status, str) else getattr(t.status, "value", t.status),
                "note": t.note,
                "meta": getattr(t, "meta", "") or "",
                "date": t.created_at.isoformat() if t.created_at else "",
            }
            for t in txns
        ]
    ).to_excel(txns_path, index=False)

    return {"users": str(users_path.resolve()), "transactions": str(txns_path.resolve())}
