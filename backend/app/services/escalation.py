from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    Category,
    Complaint,
    EscalationHierarchy,
    Role,
    SLAStatus,
    Status,
    User,
)
from app.services.audit import log_action
from app.services.notify import (
    notify_escalation,
    notify_sla_at_risk,
)


TERMINAL_STATUSES = {
    Status.RESOLVED,
    Status.CLOSED,
}


# --------------------------------------------------
# Normalize datetime to naive UTC
# --------------------------------------------------


def _to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    return value


# --------------------------------------------------
# Get active administrators
# --------------------------------------------------


def _active_admin_ids(db: Session) -> list[int]:
    return [
        row.id
        for row in (
            db.query(User.id)
            .filter(
                User.role == Role.ADMIN,
                User.is_active.is_(True),
            )
            .all()
        )
    ]


# --------------------------------------------------
# Get applicable escalation hierarchy
# --------------------------------------------------


def _get_hierarchy(
    db: Session,
    complaint: Complaint,
) -> list[EscalationHierarchy]:
    # Category-specific hierarchy takes priority.

    if complaint.category_id is not None:
        rows = (
            db.query(EscalationHierarchy)
            .filter(
                EscalationHierarchy.category_id == complaint.category_id,
                EscalationHierarchy.is_active.is_(True),
            )
            .order_by(EscalationHierarchy.level.asc())
            .all()
        )

        if rows:
            return rows

    # Otherwise use department hierarchy.

    department = complaint.assigned_department

    if not department and complaint.category_id is not None:
        category = db.get(Category, complaint.category_id)

        department = category.department if category else None

    if not department:
        return []

    return (
        db.query(EscalationHierarchy)
        .filter(
            EscalationHierarchy.category_id.is_(None),
            EscalationHierarchy.department.ilike(department),
            EscalationHierarchy.is_active.is_(True),
        )
        .order_by(EscalationHierarchy.level.asc())
        .all()
    )


# --------------------------------------------------
# Send 80% SLA warning (REQ-28)
# --------------------------------------------------


def send_sla_warning(
    db: Session,
    complaint: Complaint,
) -> bool:
    if complaint.sla_warning_sent:
        return False

    if complaint.is_archived:
        return False

    if complaint.status in TERMINAL_STATUSES:
        return False

    if complaint.sla_paused_at is not None:
        return False

    if complaint.assignee_id is None:
        return False

    if complaint.sla_status != SLAStatus.AT_RISK:
        return False

    # Prevent duplicate warning events.

    existing_event = (
        db.query(AuditLog)
        .filter_by(
            complaint_id=complaint.id,
            action="SLA_WARNING_SENT",
        )
        .first()
    )

    if existing_event:
        complaint.sla_warning_sent = True
        return False

    warning_log = log_action(
        db,
        action="SLA_WARNING_SENT",
        complaint_id=complaint.id,
        actor_id=None,
        trigger_type="Automatic",
    )

    db.flush()

    notify_sla_at_risk(
        db,
        complaint_id=complaint.id,
        reference_id=complaint.reference_id,
        recipient_id=complaint.assignee_id,
        event_id=str(warning_log.id),
    )

    complaint.sla_warning_sent = True

    return True


# --------------------------------------------------
# Escalate complaint to next hierarchy level
# --------------------------------------------------


def escalate_complaint(
    db: Session,
    complaint: Complaint,
    *,
    actor_id: int | None = None,
    reason: str | None = None,
    trigger_type: str = "Automatic",
) -> bool:
    if complaint.is_archived:
        return False

    if complaint.status in TERMINAL_STATUSES:
        return False

    # Automatic escalation requires an SLA deadline.
    # Manual escalation does not.

    if complaint.sla_deadline is None and trigger_type == "Automatic":
        return False

    if complaint.sla_paused_at is not None:
        return False

    hierarchy = _get_hierarchy(db, complaint)

    if not hierarchy:
        return False

    # Select the next configured level.

    next_level = next(
        (item for item in hierarchy if item.level > complaint.escalation_level),
        None,
    )

    if next_level is None:
        return False

    # Resolve the next escalation recipient.

    new_assignee = None

    if next_level.assignee_id is not None:
        new_assignee = db.get(User, next_level.assignee_id)

        if (
            new_assignee is None
            or not new_assignee.is_active
            or new_assignee.role != Role.STAFF
        ):
            return False

    elif next_level.department:
        department_exists = (
            db.query(User.id)
            .filter(
                User.role == Role.STAFF,
                User.is_active.is_(True),
                User.department.ilike(next_level.department),
            )
            .first()
        )

        if not department_exists:
            return False

    else:
        return False

    old_assignee_id = complaint.assignee_id
    old_department = complaint.assigned_department

    old_owner = (
        f"user:{old_assignee_id}"
        if old_assignee_id is not None
        else (f"department:{old_department}" if old_department else None)
    )

    # Update complaint ownership.

    complaint.escalation_level = next_level.level
    complaint.status = Status.ESCALATED

    if new_assignee is not None:
        complaint.assignee_id = new_assignee.id
        complaint.assigned_department = None

    else:
        complaint.assignee_id = None
        complaint.assigned_department = next_level.department

    new_owner = (
        f"user:{complaint.assignee_id}"
        if complaint.assignee_id is not None
        else f"department:{complaint.assigned_department}"
    )

    # Create audit event (REQ-30).

    event = log_action(
        db,
        action="COMPLAINT_ESCALATED",
        complaint_id=complaint.id,
        actor_id=actor_id,
        from_value=old_owner,
        to_value=new_owner,
        trigger_type=trigger_type,
        reason=(
            reason or f"Escalated to {next_level.role_name}; level {next_level.level}"
        ),
    )

    db.flush()

    # Notify administrators, previous assignee and new assignee.

    recipients = set(_active_admin_ids(db))

    if old_assignee_id is not None:
        recipients.add(old_assignee_id)

    if complaint.assignee_id is not None:
        recipients.add(complaint.assignee_id)

    elif complaint.assigned_department:
        department_staff = (
            db.query(User.id)
            .filter(
                User.role == Role.STAFF,
                User.is_active.is_(True),
                User.department.ilike(complaint.assigned_department),
            )
            .all()
        )

        recipients.update(row.id for row in department_staff)

    notify_escalation(
        db,
        complaint_id=complaint.id,
        reference_id=complaint.reference_id,
        recipient_ids=sorted(recipients),
        event_id=str(event.id),
    )

    return True


# --------------------------------------------------
# Process SLA warning and automatic escalation
# --------------------------------------------------


def process_sla_complaint(
    db: Session,
    complaint: Complaint,
    now: datetime,
) -> dict:
    if complaint.is_archived:
        return {
            "warning_sent": False,
            "escalated": False,
        }

    if complaint.status in TERMINAL_STATUSES:
        return {
            "warning_sent": False,
            "escalated": False,
        }

    if complaint.sla_deadline is None:
        return {
            "warning_sent": False,
            "escalated": False,
        }

    if complaint.sla_paused_at is not None:
        return {
            "warning_sent": False,
            "escalated": False,
        }

    now = _to_naive_utc(now)
    deadline = _to_naive_utc(complaint.sla_deadline)

    # SLA deadline breached.

    if now >= deadline:
        complaint.sla_status = SLAStatus.BREACHED

        escalated = escalate_complaint(
            db,
            complaint,
            trigger_type="Automatic",
        )

        return {
            "warning_sent": False,
            "escalated": escalated,
        }

    # SLA warning at 80% elapsed.
    # The SLA status should already have been updated by
    # the SLA classification logic.

    warning_sent = False

    if complaint.sla_status == SLAStatus.AT_RISK:
        warning_sent = send_sla_warning(
            db,
            complaint,
        )

    return {
        "warning_sent": warning_sent,
        "escalated": False,
    }
