from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.db.models import User
from backend.app.services import redis_client
from backend.app.services.wallet_service import SERVICE_IDS

bearer = HTTPBearer(auto_error=False)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def rate_limit(request: Request, bucket: str, limit: int = 60, window: int = 60) -> None:
    ip = client_ip(request) or "unknown"
    key = f"rl:{bucket}:{ip}"
    count = redis_client.incr(key, ttl=window)
    if count > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_access_token(creds.credentials)
        user_id = payload.get("sub")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.get(User, user_id)
    if not user or user.id in SERVICE_IDS or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
