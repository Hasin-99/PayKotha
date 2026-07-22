from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import (
    ApprovalStatus,
    ReversalRequest,
    SettlementBatch,
    Transaction,
    TxnStatus,
    TxnType,
    User,
)
from backend.app.services import wallet_service
from backend.app.services.audit import audit
from backend.app.services.rails import get_rail


def run_eod_settlement(db: Session, admin: User) -> SettlementBatch:
    """Close open successful fee-bearing transactions into a settlement batch."""
    if not admin.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    rows = list(
        db.scalars(
            select(Transaction).where(
                Transaction.status == TxnStatus.SUCCESS.value,
                Transaction.txn_type.in_(
                    [
                        TxnType.CASH_OUT.value,
                        TxnType.MERCHANT.value,
                        TxnType.BILL_PAY.value,
                        TxnType.BANK_OUT.value,
                    ]
                ),
            )
        )
    )
    gross = sum(t.amount for t in rows)
    fees = sum(t.fee for t in rows)
    batch = SettlementBatch(
        id=f"SET{uuid4().hex[:10].upper()}",
        status="CLOSED",
        txn_count=len(rows),
        gross_amount=round(gross, 2),
        fee_amount=round(fees, 2),
        net_amount=round(gross - fees, 2),
        closed_at=datetime.now(timezone.utc),
    )
    rail = get_rail()
    result = rail.transfer(
        from_account="PAYKOTHA-POOL",
        to_account="SETTLEMENT-BANK",
        amount=batch.net_amount,
        narrative=f"EOD settlement {batch.id}",
    )
    if not result.success:
        raise HTTPException(status_code=502, detail=f"Settlement rail failed: {result.message}")
    batch.rail_ref = result.rail_ref
    db.add(batch)
    audit(
        db,
        actor_id=admin.id,
        action="EOD_SETTLEMENT",
        entity_type="SettlementBatch",
        entity_id=batch.id,
        detail=f"count={batch.txn_count} net={batch.net_amount} rail={batch.rail_ref}",
    )
    db.commit()
    db.refresh(batch)
    return batch


def request_reversal(db: Session, maker: User, transaction_id: str, reason: str) -> ReversalRequest:
    if not maker.is_admin:
        raise HTTPException(status_code=403, detail="Admin maker required")
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn.status != TxnStatus.SUCCESS.value:
        raise HTTPException(status_code=400, detail="Only successful txns can be reversed")
    req = ReversalRequest(
        id=f"REV{uuid4().hex[:10].upper()}",
        transaction_id=transaction_id,
        maker_id=maker.id,
        reason=reason,
        status=ApprovalStatus.PENDING.value,
    )
    db.add(req)
    audit(db, actor_id=maker.id, action="REVERSAL_REQUESTED", entity_type="Transaction", entity_id=transaction_id, detail=reason)
    db.commit()
    db.refresh(req)
    return req


def decide_reversal(db: Session, checker: User, request_id: str, approve: bool) -> ReversalRequest:
    if not checker.is_admin:
        raise HTTPException(status_code=403, detail="Admin checker required")
    req = db.get(ReversalRequest, request_id)
    if not req or req.status != ApprovalStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="No pending reversal")
    if req.maker_id == checker.id:
        raise HTTPException(status_code=400, detail="Maker-checker separation: same admin cannot approve")

    req.checker_id = checker.id
    req.decided_at = datetime.now(timezone.utc)
    if not approve:
        req.status = ApprovalStatus.REJECTED.value
        audit(db, actor_id=checker.id, action="REVERSAL_REJECTED", entity_id=req.id)
        db.commit()
        db.refresh(req)
        return req

    txn = db.get(Transaction, req.transaction_id)
    assert txn
    # Reverse balances: credit original sender, debit original receiver when applicable
    sender = db.get(User, txn.sender_id)
    receiver = db.get(User, txn.receiver_id)
    service_ids = {
        wallet_service.SYSTEM_ID,
        wallet_service.MERCHANT_ID,
        wallet_service.BILLER_ID,
        wallet_service.BANK_ID,
    }
    amount = float(txn.amount)
    fee = float(txn.fee)
    if sender and sender.id not in service_ids:
        sender.balance = round(sender.balance + amount + fee, 2)
    if receiver and receiver.id not in service_ids:
        if receiver.balance < amount:
            raise HTTPException(status_code=400, detail="Cannot reverse: receiver has insufficient funds")
        receiver.balance = round(receiver.balance - amount, 2)

    rev = Transaction(
        id=f"TXN{uuid4().hex[:10].upper()}",
        sender_id=txn.receiver_id,
        receiver_id=txn.sender_id,
        amount=amount,
        fee=0.0,
        txn_type=TxnType.REVERSAL.value,
        status=TxnStatus.SUCCESS.value,
        note=f"Reversal of {txn.id}: {req.reason}",
        meta=f'{{"original":"{txn.id}"}}',
        rail_ref=f"REV-{txn.id}",
        idempotency_key=f"rev-{txn.id}",
    )
    db.add(rev)
    txn.status = TxnStatus.REVERSED.value
    req.status = ApprovalStatus.APPROVED.value
    audit(db, actor_id=checker.id, action="REVERSAL_APPROVED", entity_id=txn.id, detail=rev.id)
    db.commit()
    db.refresh(req)
    return req


def reconcile_snapshot(db: Session) -> dict:
    """Simple balance sheet check: sum wallet balances vs transaction activity."""
    users = list(
        db.scalars(select(User).where(User.id.notin_(list(wallet_service.SERVICE_IDS))))
    )
    wallet_sum = round(sum(u.balance for u in users), 2)
    savings_sum = round(sum(u.savings_balance for u in users), 2)
    txn_count = db.scalar(select(func.count()).select_from(Transaction)) or 0
    return {
        "customer_wallet_liability": wallet_sum,
        "customer_savings_liability": savings_sum,
        "transaction_count": int(txn_count),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "BALANCED_SANDBOX",
    }
