from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from backend.app.core.config import get_settings


def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_pin(pin: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pin.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, extra: Optional[dict[str, Any]] = None) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire, "typ": "access"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": subject, "exp": expire, "typ": "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str, *, expected_typ: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    if expected_typ:
        typ = payload.get("typ")
        if typ is not None and typ != expected_typ:
            raise JWTError("Unexpected token type")
    return payload


def decode_access_token(token: str) -> dict[str, Any]:
    return decode_token(token, expected_typ="access")
