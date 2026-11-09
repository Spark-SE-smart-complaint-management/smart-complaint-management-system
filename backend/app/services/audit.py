from sqlalchemy.orm import Session

from app.models import AuditLog


def log_action(
    db: Session,
    *,
    action: str,
    complaint_id: int | None = None,
    actor_id: int | None = None,
    from_value: str | None = None,
    to_value: str | None = None,
    trigger_type: str | None = None,
    reason: str | None = None,
) -> AuditLog:
    """Append one row to the audit trail (REQ-19, REQ-30). Caller commits."""
    entry = AuditLog(
        action=action, complaint_id=complaint_id, actor_id=actor_id,
        from_value=from_value, to_value=to_value,
        trigger_type=trigger_type, reason=reason,
    )
    db.add(entry)
    return entry
