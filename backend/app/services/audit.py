"""
Helpers for persisting audit logs.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models.models import AuditLog


def log_audit(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(entry)
    db.flush()
    return entry
