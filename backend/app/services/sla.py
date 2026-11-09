"""SLA helpers (REQ-15, REQ-16). Issue #8 builds on these (business hours, pause, reports)."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Complaint, Priority, SLAPolicy, SLAStatus
from app.services.audit import log_action

AT_RISK_FRACTION = 0.8  # REQ-28 / REQ-32: At Risk once 80% of the SLA has elapsed


def now_utc() -> datetime:
    """Naive UTC, matching how SQLite returns stored DateTimes."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def get_sla_hours(db: Session, category_id: int | None, priority: Priority | None) -> int | None:
    if category_id is None or priority is None:
        return None
    policy = (
        db.query(SLAPolicy)
        .filter(SLAPolicy.category_id == category_id, SLAPolicy.priority == priority)
        .first()
    )
    return policy.duration_hours if policy else None


def compute_sla_deadline(db: Session, category_id, priority, start: datetime) -> datetime | None:
    hours = get_sla_hours(db, category_id, priority)
    if hours is None:
        return None
    return to_naive_utc(start) + timedelta(hours=hours)


def classify_sla(created_at: datetime, deadline: datetime | None, now: datetime | None = None) -> SLAStatus | None:
    if deadline is None:
        return None
    now = now or now_utc()
    created_at = to_naive_utc(created_at)
    deadline = to_naive_utc(deadline)
    if now >= deadline:
        return SLAStatus.BREACHED
    total = (deadline - created_at).total_seconds()
    if total > 0 and (now - created_at).total_seconds() / total >= AT_RISK_FRACTION:
        return SLAStatus.AT_RISK
    return SLAStatus.ON_TRACK


def recompute_sla(db: Session, complaint: Complaint, actor_id: int | None, trigger_type: str = "Manual") -> None:
    """REQ-16: call whenever category or priority changes. Caller commits.

    The deadline is measured from the complaint's created_at.
    The warning flag is reset because the deadline moved.
    """
    old = complaint.sla_deadline
    new = compute_sla_deadline(db, complaint.category_id, complaint.priority, complaint.created_at)
    complaint.sla_deadline = new
    complaint.sla_status = classify_sla(complaint.created_at, new)
    complaint.sla_warning_sent = False
    log_action(
        db, action="SLA_RECOMPUTE", complaint_id=complaint.id, actor_id=actor_id,
        from_value=old.isoformat() if old else None,
        to_value=new.isoformat() if new else None,
        trigger_type=trigger_type,
    )