from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.models import OtpChallenge
from backend.app.services import redis_client


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def issue_otp(db: Session, user_id: str, purpose: str) -> dict:
    """Issue OTP. In production this would go through SMS gateway; sandbox returns code."""
    settings = get_settings()
    code = "".join(secrets.choice("0123456789") for _ in range(settings.otp_length))
    challenge_id = f"OTP{uuid4().hex[:10].upper()}"
    expires = datetime.now(timezone.utc) + timedelta(seconds=settings.otp_ttl_seconds)
    row = OtpChallenge(
        id=challenge_id,
        user_id=user_id,
        purpose=purpose,
        code_hash=_hash_code(code),
        expires_at=expires,
    )
    db.add(row)
    db.commit()

    # Store mirror in redis if available (fast path)
    redis_client.set_json(f"otp:{challenge_id}", {"user_id": user_id, "purpose": purpose}, settings.otp_ttl_seconds)

    payload = {
        "challenge_id": challenge_id,
        "expires_in": settings.otp_ttl_seconds,
        "purpose": purpose,
        "delivery": "SANDBOX_SMS",
    }
    if settings.app_env != "production":
        payload["sandbox_code"] = code  # never expose in real prod
    return payload


def verify_otp(db: Session, challenge_id: str, code: str, user_id: str, purpose: str) -> None:
    row = db.get(OtpChallenge, challenge_id)
    if not row or row.user_id != user_id or row.purpose != purpose:
        raise HTTPException(status_code=400, detail="Invalid OTP challenge")
    if row.consumed:
        raise HTTPException(status_code=400, detail="OTP already used")
    exp = row.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > exp:
        raise HTTPException(status_code=400, detail="OTP expired")
    if _hash_code(code) != row.code_hash:
        raise HTTPException(status_code=400, detail="Incorrect OTP")
    row.consumed = True
    db.commit()
