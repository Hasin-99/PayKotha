from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.db.models import AuditLog


def audit(
    db: Session,
    *,
    actor_id: str,
    action: str,
    entity_type: str = "",
    entity_id: str = "",
    detail: str = "",
    ip: str = "",
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
            ip=ip,
        )
    )
