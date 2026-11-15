"""SLA helpers for deadline calculation, monitoring and business-hours mode."""
import os
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.models import Complaint, Priority, SLAPolicy, SLAStatus
from app.services.audit import log_action

AT_RISK_FRACTION = float(os.getenv("SLA_AT_RISK_FRACTION", "0.8"))
if not 0 < AT_RISK_FRACTION < 1:
    raise RuntimeError("SLA_AT_RISK_FRACTION must be between 0 and 1")


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_naive_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


def _business_settings():
    enabled = os.getenv("SLA_BUSINESS_HOURS_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
    timezone_name = os.getenv("SLA_TIMEZONE", "UTC")
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(f"Unknown SLA_TIMEZONE: {timezone_name}") from exc
    start = time.fromisoformat(os.getenv("SLA_WORKDAY_START", "09:00"))
    end = time.fromisoformat(os.getenv("SLA_WORKDAY_END", "17:00"))
    if start >= end:
        raise RuntimeError("SLA_WORKDAY_START must be earlier than SLA_WORKDAY_END")
    weekdays = {
        int(value.strip())
        for value in os.getenv("SLA_WORKING_DAYS", "0,1,2,3,4").split(",")
        if value.strip()
    }
    if not weekdays or any(day not in range(7) for day in weekdays):
        raise RuntimeError("SLA_WORKING_DAYS must contain weekday numbers 0 through 6")
    holidays = set()
    for value in os.getenv("SLA_HOLIDAYS", "").split(","):
        if value.strip():
            holidays.add(date.fromisoformat(value.strip()))
    return enabled, zone, start, end, weekdays, holidays


def _add_business_hours(start_utc: datetime, hours: int) -> datetime:
    enabled, zone, work_start, work_end, weekdays, holidays = _business_settings()
    if not enabled:
        return start_utc + timedelta(hours=hours)

    remaining = timedelta(hours=hours)
    local = start_utc.replace(tzinfo=timezone.utc).astimezone(zone)
    while remaining > timedelta(0):
        if local.weekday() not in weekdays or local.date() in holidays:
            local = datetime.combine(local.date() + timedelta(days=1), work_start, tzinfo=zone)
            continue
        day_start = datetime.combine(local.date(), work_start, tzinfo=zone)
        day_end = datetime.combine(local.date(), work_end, tzinfo=zone)
        if local < day_start:
            local = day_start
        if local >= day_end:
            local = datetime.combine(local.date() + timedelta(days=1), work_start, tzinfo=zone)
            continue
        available = day_end.astimezone(timezone.utc) - local.astimezone(timezone.utc)
        consumed = min(remaining, available)
        local = (local.astimezone(timezone.utc) + consumed).astimezone(zone)
        remaining -= consumed
        if remaining > timedelta(0) and local >= day_end:
            local = datetime.combine(local.date() + timedelta(days=1), work_start, tzinfo=zone)
    return local.astimezone(timezone.utc).replace(tzinfo=None)


def get_sla_hours(db: Session, category_id: int | None, priority: Priority | None) -> int | None:
    if category_id is None or priority is None:
        return None
    policy = db.query(SLAPolicy).filter(
        SLAPolicy.category_id == category_id, SLAPolicy.priority == priority
    ).first()
    return policy.duration_hours if policy else None


def compute_sla_deadline(db: Session, category_id, priority, start: datetime) -> datetime | None:
    hours = get_sla_hours(db, category_id, priority)
    return _add_business_hours(to_naive_utc(start), hours) if hours is not None else None


def classify_sla(created_at: datetime, deadline: datetime | None, now: datetime | None = None) -> SLAStatus | None:
    if deadline is None:
        return None
    now = to_naive_utc(now or now_utc())
    created_at, deadline = to_naive_utc(created_at), to_naive_utc(deadline)
    if now >= deadline:
        return SLAStatus.BREACHED
    total = (deadline - created_at).total_seconds()
    elapsed = (now - created_at).total_seconds()
    if total > 0 and elapsed / total >= AT_RISK_FRACTION:
        return SLAStatus.AT_RISK
    return SLAStatus.ON_TRACK


def get_sla_timer(complaint: Complaint, now: datetime | None = None) -> dict:
    """Return elapsed/remaining wall-clock seconds and live breach state."""
    now = to_naive_utc(now or now_utc())
    created = to_naive_utc(complaint.created_at)
    raw_deadline = getattr(complaint, "sla_deadline", None)
    deadline = to_naive_utc(raw_deadline) if raw_deadline is not None else None
    paused_at = getattr(complaint, "sla_paused_at", None)
    effective_now = min(now, to_naive_utc(paused_at)) if paused_at is not None else now
    elapsed = max(0, int((effective_now - created).total_seconds()))
    if deadline is None:
        return {"sla_elapsed_seconds": elapsed, "sla_remaining_seconds": None, "sla_breach_state": "Not Tracked"}
    remaining = max(0, int((deadline - effective_now).total_seconds()))
    state = classify_sla(created, deadline, effective_now)
    return {"sla_elapsed_seconds": elapsed, "sla_remaining_seconds": remaining, "sla_breach_state": state.value}


def recompute_sla(db: Session, complaint: Complaint, actor_id: int | None, trigger_type: str = "Manual") -> None:
    """REQ-16: recompute when category or priority changes. Caller commits."""
    old = complaint.sla_deadline
    new = compute_sla_deadline(db, complaint.category_id, complaint.priority, complaint.created_at)
    complaint.sla_deadline = new
    complaint.sla_status = classify_sla(complaint.created_at, new)
    complaint.sla_warning_sent = False
    log_action(db, action="SLA_RECOMPUTE", complaint_id=complaint.id, actor_id=actor_id,
               from_value=old.isoformat() if old else None,
               to_value=new.isoformat() if new else None, trigger_type=trigger_type)
