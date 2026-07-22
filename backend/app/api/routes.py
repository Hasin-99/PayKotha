from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import client_ip, get_admin_user, get_current_user, rate_limit
from backend.app.core.config import get_settings
from backend.app.core.database import get_db
from backend.app.core.security import create_access_token, create_refresh_token, decode_token
from backend.app.db.models import AuditLog, ReversalRequest, SettlementBatch, User
from backend.app.schemas.wallet import (
    AmountRequest,
    AuditOut,
    BankInRequest,
    BankOutRequest,
    BillPayRequest,
    ChangePinRequest,
    DonationRequest,
    FavoriteIn,
    FavoriteOut,
    KycUpgradeRequest,
    LoginRequest,
    MerchantPayRequest,
    MoneyRequestOut,
    NotificationOut,
    OtpIssueRequest,
    OtpIssueResponse,
    PlatformStats,
    RechargeRequest,
    RefreshRequest,
    RegisterRequest,
    RequestMoneyCreate,
    ReversalCreate,
    ReversalDecide,
    ReversalOut,
    SettlementOut,
    TokenResponse,
    TransactionOut,
    TransferRequest,
    UserPublic,
)
from backend.app.services import banking_ops, otp_service, wallet_service
from backend.app.services.excel_export import export_to_excel

router = APIRouter()


def _txn(t) -> TransactionOut:
    return TransactionOut(
        id=t.id,
        sender_id=t.sender_id,
        receiver_id=t.receiver_id,
        amount=t.amount,
        fee=t.fee,
        txn_type=t.txn_type,
        status=t.status,
        note=t.note,
        meta=getattr(t, "meta", "") or "",
        rail_ref=getattr(t, "rail_ref", "") or "",
        created_at=t.created_at,
    )


def _tokens(user: User) -> TokenResponse:
    settings = get_settings()
    extra = {"phone": user.phone, "name": user.name, "admin": user.is_admin, "kyc": user.kyc_level}
    return TokenResponse(
        access_token=create_access_token(user.id, extra),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "env": settings.app_env,
        "rail_mode": settings.rail_mode,
        "grade": "sandbox-core-banking",
    }


@router.get("/catalog")
def catalog():
    return wallet_service.catalog()


@router.post("/auth/register", response_model=UserPublic)
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "register", limit=20, window=3600)
    return wallet_service.register_user(
        db,
        body.name,
        body.phone,
        body.pin,
        body.opening_balance,
        nid_number=body.nid_number,
        device_id=body.device_id,
    )


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "login", limit=40, window=300)
    user = wallet_service.authenticate(
        db, body.phone, body.pin, ip=client_ip(request), device_id=body.device_id
    )
    return _tokens(user)


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token, expected_typ="refresh")
    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return _tokens(user)


@router.post("/auth/change-pin", response_model=UserPublic)
def change_pin(body: ChangePinRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return wallet_service.change_pin(db, user, body.old_pin, body.new_pin)


@router.post("/auth/otp/issue", response_model=OtpIssueResponse)
def issue_otp(body: OtpIssueRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if body.purpose not in {"TRANSFER", "CASH_OUT", "LOGIN"}:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Invalid OTP purpose")
    return OtpIssueResponse(**otp_service.issue_otp(db, user.id, body.purpose))


@router.post("/kyc/upgrade", response_model=UserPublic)
def kyc_upgrade(body: KycUpgradeRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return wallet_service.upgrade_kyc(db, user, body.level, body.nid_number)


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/wallet/cash-in", response_model=TransactionOut)
def cash_in(body: AmountRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _txn(wallet_service.cash_in(db, user, body.amount, body.note, body.idempotency_key))


@router.post("/wallet/cash-out", response_model=TransactionOut)
def cash_out(body: AmountRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _txn(
        wallet_service.cash_out(
            db,
            user,
            body.amount,
            body.note,
            body.idempotency_key,
            otp_challenge_id=body.otp_challenge_id,
            otp_code=body.otp_code,
        )
    )


@router.post("/wallet/send", response_model=TransactionOut)
def send(body: TransferRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _txn(
        wallet_service.send_money(
            db,
            user,
            body.receiver_phone,
            body.amount,
            body.note,
            body.idempotency_key,
            otp_challenge_id=body.otp_challenge_id,
            otp_code=body.otp_code,
        )
    )


@router.post("/wallet/recharge", response_model=TransactionOut)
def recharge(body: RechargeRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _txn(
        wallet_service.mobile_recharge(db, user, body.operator, body.mobile, body.amount, body.idempotency_key)
    )


@router.post("/wallet/bill-pay", response_model=TransactionOut)
def bill_pay(body: BillPayRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _txn(
        wallet_service.bill_pay(db, user, body.biller_code, body.account_no, body.amount, body.idempotency_key)
    )


@router.post("/wallet/merchant-pay", response_model=TransactionOut)
def merchant_pay(body: MerchantPayRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _txn(
        wallet_service.merchant_pay(db, user, body.merchant_code, body.amount, body.note, body.idempotency_key)
    )


@router.post("/wallet/bank-transfer", response_model=TransactionOut)
def bank_out(body: BankOutRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _txn(
        wallet_service.bank_transfer_out(
            db,
            user,
            body.bank_account,
            body.amount,
            body.idempotency_key,
            otp_challenge_id=body.otp_challenge_id,
            otp_code=body.otp_code,
        )
    )


@router.post("/wallet/add-money", response_model=TransactionOut)
def bank_in(body: BankInRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _txn(wallet_service.add_money_from_bank(db, user, body.amount, body.bank_account, body.idempotency_key))


@router.post("/wallet/donate", response_model=TransactionOut)
def donate(body: DonationRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _txn(wallet_service.donate(db, user, body.cause, body.amount, body.idempotency_key))


@router.post("/wallet/savings/deposit", response_model=TransactionOut)
def savings_in(body: AmountRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _txn(wallet_service.savings_deposit(db, user, body.amount, body.idempotency_key))


@router.post("/wallet/savings/withdraw", response_model=TransactionOut)
def savings_out(body: AmountRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _txn(wallet_service.savings_withdraw(db, user, body.amount, body.idempotency_key))


@router.get("/wallet/transactions", response_model=list[TransactionOut])
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_txn(t) for t in wallet_service.list_transactions(db, user)]


@router.post("/requests", response_model=MoneyRequestOut)
def create_request(body: RequestMoneyCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return wallet_service.create_money_request(db, user, body.payer_phone, body.amount, body.note)


@router.get("/requests", response_model=list[MoneyRequestOut])
def list_requests(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return wallet_service.list_money_requests(db, user)


@router.post("/requests/{request_id}/pay", response_model=TransactionOut)
def pay_request(request_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _txn(wallet_service.pay_money_request(db, user, request_id))


@router.post("/requests/{request_id}/cancel", response_model=MoneyRequestOut)
def cancel_request(request_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return wallet_service.cancel_money_request(db, user, request_id)


@router.get("/favorites", response_model=list[FavoriteOut])
def favorites(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return wallet_service.list_favorites(db, user)


@router.post("/favorites", response_model=FavoriteOut)
def add_fav(body: FavoriteIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return wallet_service.add_favorite(db, user, body.label, body.phone, body.kind)


@router.delete("/favorites/{fav_id}")
def del_fav(fav_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    wallet_service.delete_favorite(db, user, fav_id)
    return {"ok": True}


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return wallet_service.list_notifications(db, user)


@router.post("/notifications/read")
def read_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"marked": wallet_service.mark_notifications_read(db, user)}


@router.get("/live/snapshot")
def live_snapshot(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Single-poll live wallet state for reactive UIs."""
    db.refresh(user)
    unread = sum(1 for n in wallet_service.list_notifications(db, user, limit=50) if not n.is_read)
    recent = wallet_service.list_transactions(db, user, limit=8)
    pending_reqs = [r for r in wallet_service.list_money_requests(db, user) if r.status == "PENDING"]
    return {
        "server_time": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "live": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "phone": user.phone,
            "balance": user.balance,
            "savings_balance": user.savings_balance,
            "daily_limit": user.daily_limit,
            "kyc_level": user.kyc_level,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "bank_account": user.bank_account,
            "created_at": user.created_at,
        },
        "unread_notifications": unread,
        "pending_requests": len(pending_reqs),
        "recent": [_txn(t) for t in recent],
    }


@router.get("/live/stream")
async def live_stream(request: Request, token: str):
    """Server-Sent Events — push balance/inbox changes like a live MFS app."""
    import asyncio
    import json
    from datetime import datetime, timezone

    from fastapi.responses import StreamingResponse
    from jose import JWTError

    from backend.app.core.database import SessionLocal
    from backend.app.core.security import decode_access_token
    from backend.app.services import live_bus

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
    except JWTError:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Invalid stream token")

    async def event_gen():
        q = live_bus.subscribe(user_id)
        last_fp = None
        try:
            while True:
                if await request.is_disconnected():
                    break
                db = SessionLocal()
                try:
                    user = db.get(User, user_id)
                    if not user or not user.is_active:
                        yield f"event: error\ndata: {json.dumps({'detail': 'user inactive'})}\n\n"
                        break
                    notifs = wallet_service.list_notifications(db, user, limit=20)
                    unread = sum(1 for n in notifs if not n.is_read)
                    recent = wallet_service.list_transactions(db, user, limit=8)
                    snap = {
                        "type": "SNAPSHOT",
                        "server_time": datetime.now(timezone.utc).isoformat(),
                        "balance": user.balance,
                        "savings_balance": user.savings_balance,
                        "unread_notifications": unread,
                        "latest_notif": (
                            {"title": notifs[0].title, "body": notifs[0].body} if notifs else None
                        ),
                        "recent": [
                            {
                                "id": t.id,
                                "txn_type": t.txn_type,
                                "amount": t.amount,
                                "fee": t.fee,
                                "note": t.note,
                                "status": t.status,
                                "created_at": t.created_at.isoformat() if t.created_at else None,
                            }
                            for t in recent
                        ],
                    }
                    fp = f"{snap['balance']}:{snap['savings_balance']}:{unread}:{recent[0].id if recent else '-'}"
                finally:
                    db.close()

                if fp != last_fp:
                    last_fp = fp
                    yield f"event: wallet\ndata: {json.dumps(snap)}\n\n"

                try:
                    evt = await asyncio.wait_for(q.get(), timeout=1.25)
                    yield f"event: ping\ndata: {json.dumps(evt)}\n\n"
                except asyncio.TimeoutError:
                    yield f"event: heartbeat\ndata: {json.dumps({'t': datetime.now(timezone.utc).isoformat()})}\n\n"
        finally:
            live_bus.unsubscribe(user_id, q)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Admin / ops (maker-checker, settlement, recon) ─────────────────────────


@router.get("/admin/stats", response_model=PlatformStats)
def stats(db: Session = Depends(get_db), _: User = Depends(get_admin_user)):
    return PlatformStats(**wallet_service.platform_stats(db))


@router.post("/admin/export-excel")
def excel_export(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    paths = export_to_excel(db)
    return {"message": "Exported for course/Excel requirement", "paths": paths, "by": user.id}


@router.post("/admin/settlement/eod", response_model=SettlementOut)
def eod_settlement(db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    return banking_ops.run_eod_settlement(db, admin)


@router.get("/admin/settlement", response_model=list[SettlementOut])
def list_settlements(db: Session = Depends(get_db), _: User = Depends(get_admin_user)):
    rows = list(db.scalars(select(SettlementBatch).order_by(SettlementBatch.created_at.desc()).limit(50)))
    return rows


@router.get("/admin/reconcile")
def reconcile(db: Session = Depends(get_db), _: User = Depends(get_admin_user)):
    return banking_ops.reconcile_snapshot(db)


@router.post("/admin/reversals", response_model=ReversalOut)
def create_reversal(body: ReversalCreate, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    return banking_ops.request_reversal(db, admin, body.transaction_id, body.reason)


@router.post("/admin/reversals/{request_id}/decide", response_model=ReversalOut)
def decide_reversal(
    request_id: str,
    body: ReversalDecide,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    return banking_ops.decide_reversal(db, admin, request_id, body.approve)


@router.get("/admin/reversals", response_model=list[ReversalOut])
def list_reversals(db: Session = Depends(get_db), _: User = Depends(get_admin_user)):
    return list(db.scalars(select(ReversalRequest).order_by(ReversalRequest.created_at.desc()).limit(50)))


@router.get("/admin/audit", response_model=list[AuditOut])
def list_audit(db: Session = Depends(get_db), _: User = Depends(get_admin_user)):
    return list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)))
