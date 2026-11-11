
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import REOPEN_GRACE_PERIOD_DAYS
from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import AuditLog, Complaint, Role, Status, User
from app.schemas import ComplaintHistoryOut, ComplaintStatusUpdateIn
from app.services.audit import log_action

router = APIRouter(prefix="/complaints", tags=["complaint-status"])

staff_or_admin = require_role(Role.STAFF, Role.ADMIN)
admin_only = require_role(Role.ADMIN)

VALID_TRANSITIONS = {
    Status.NEW: {
        Status.ASSIGNED,
        Status.IN_PROGRESS,
        Status.ESCALATED,
    },
    Status.ASSIGNED: {
        Status.IN_PROGRESS,
        Status.ESCALATED,
    },
    Status.IN_PROGRESS: {
        Status.ESCALATED,
        Status.RESOLVED,
    },
    Status.ESCALATED: {
        Status.IN_PROGRESS,
        Status.RESOLVED,
    },
    Status.RESOLVED: {
        Status.CLOSED,
    },
    Status.CLOSED: set(),
    Status.REOPENED: {
        Status.IN_PROGRESS,
        Status.ESCALATED,
    },
}


def _get_complaint(db: Session, complaint_id: int) -> Complaint:
    complaint = db.get(Complaint, complaint_id)

    if complaint is None:
        raise HTTPException(404, "Complaint not found")

    return complaint


def _get_closure_time(db: Session, complaint_id: int):
    entry = (
        db.query(AuditLog)
        .filter(
            AuditLog.complaint_id == complaint_id,
            AuditLog.action == "STATUS_CHANGE",
            AuditLog.to_value == Status.CLOSED.value,
        )
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
        .first()
    )

    if entry is None:
        raise HTTPException(
            409,
            "Closure timestamp not found. Please contact an administrator.",
        )

    closed_at = entry.timestamp

    if closed_at.tzinfo is None:
        closed_at = closed_at.replace(tzinfo=timezone.utc)

    return closed_at


def _check_grace_period(db: Session, complaint: Complaint):
    closed_at = _get_closure_time(db, complaint.id)
    deadline = closed_at + timedelta(days=REOPEN_GRACE_PERIOD_DAYS)

    if datetime.now(timezone.utc) > deadline:
        raise HTTPException(
            409,
            detail=(
                f"The {REOPEN_GRACE_PERIOD_DAYS}-day reopening "
                "grace period has expired."
            ),
        )


def _count_previous_reopens(db: Session, complaint_id: int) -> int:
    return (
        db.query(AuditLog)
        .filter(
            AuditLog.complaint_id == complaint_id,
            AuditLog.action == "STATUS_CHANGE",
            AuditLog.from_value == Status.CLOSED.value,
            AuditLog.to_value == Status.REOPENED.value,
        )
        .count()
    )


# --------------------------------------------------
# Staff/Admin: update complaint status
# --------------------------------------------------

@router.patch("/{complaint_id}/status")
def update_complaint_status(
    complaint_id: int,
    data: ComplaintStatusUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(staff_or_admin),
):
    complaint = _get_complaint(db, complaint_id)

    if (
        user.role == Role.STAFF
        and complaint.assignee_id != user.id
    ):
        raise HTTPException(
            403,
            "Only assigned staff or an administrator can change this status",
        )

    if data.status == Status.REOPENED:
        raise HTTPException(
            403,
            "Use the complainant reopening workflow instead",
        )

    if data.status not in VALID_TRANSITIONS.get(
        complaint.status, set()
    ):
        raise HTTPException(
            409,
            f"Invalid status transition: {complaint.status.value} "
            f"to {data.status.value}",
        )

    old_status = complaint.status
    complaint.status = data.status

    log_action(
        db,
        action="STATUS_CHANGE",
        complaint_id=complaint.id,
        actor_id=user.id,
        from_value=old_status.value,
        to_value=data.status.value,
        trigger_type="Manual",
        reason=data.reason,
    )

    db.commit()
    db.refresh(complaint)

    return {
        "message": "Complaint status updated successfully",
        "complaint_id": complaint.id,
        "old_status": old_status.value,
        "new_status": complaint.status.value,
    }


# --------------------------------------------------
# View complaint status history
# --------------------------------------------------

@router.get(
    "/{complaint_id}/history",
    response_model=list[ComplaintHistoryOut],
)
def get_complaint_history(
    complaint_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    complaint = _get_complaint(db, complaint_id)

    if (
        user.role == Role.COMPLAINANT
        and complaint.complainant_id != user.id
    ):
        raise HTTPException(
            403,
            "You can only view your own complaint history",
        )

    if (
        user.role == Role.STAFF
        and complaint.assignee_id != user.id
    ):
        raise HTTPException(
            403,
            "You can only view history of complaints assigned to you",
        )

    return (
        db.query(AuditLog)
        .filter(
            AuditLog.complaint_id == complaint.id,
            AuditLog.action.in_(["STATUS_CHANGE", "COMPLAINT_ASSIGNED", "COMPLAINT_REASSIGNED"]),
        )
        .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
        .all()
    )


# --------------------------------------------------
# Complainant: request complaint reopening
# --------------------------------------------------

@router.post("/{complaint_id}/reopen")
def reopen_complaint(
    complaint_id: int,
    justification: str = Query(
        ...,
        min_length=10,
        max_length=500,
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    complaint = _get_complaint(db, complaint_id)

    if user.role != Role.COMPLAINANT:
        raise HTTPException(
            403,
            "Only the complainant can request reopening",
        )

    if complaint.complainant_id != user.id:
        raise HTTPException(
            403,
            "You can only reopen your own complaints",
        )

    if complaint.status != Status.CLOSED:
        raise HTTPException(
            409,
            "Only closed complaints can be reopened",
        )

    _check_grace_period(db, complaint)

    previous_reopens = _count_previous_reopens(
        db, complaint.id
    )

    # A later reopening requires Administrator approval.
    if previous_reopens >= 1:
        pending_request = (
            db.query(AuditLog)
            .filter(
                AuditLog.complaint_id == complaint.id,
                AuditLog.action == "REOPEN_REQUESTED",
            )
            .order_by(AuditLog.timestamp.desc())
            .first()
        )

        if pending_request is not None:
            raise HTTPException(
                409,
                "A reopening request is already awaiting administrator review.",
            )

        log_action(
            db,
            action="REOPEN_REQUESTED",
            complaint_id=complaint.id,
            actor_id=user.id,
            from_value=Status.CLOSED.value,
            to_value="Pending Approval",
            trigger_type="Complainant",
            reason=justification,
        )

        db.commit()

        return JSONResponse(
            status_code=202,
            content={
                "message": "Reopening request submitted for administrator approval",
                "complaint_id": complaint.id,
                "status": "Pending Approval",
            },
        )

    # First reopening can be completed directly.
    complaint.status = Status.REOPENED

    log_action(
        db,
        action="STATUS_CHANGE",
        complaint_id=complaint.id,
        actor_id=user.id,
        from_value=Status.CLOSED.value,
        to_value=Status.REOPENED.value,
        trigger_type="Complainant",
        reason=justification,
    )

    db.commit()
    db.refresh(complaint)

    return {
        "message": "Complaint reopened successfully",
        "complaint_id": complaint.id,
        "status": complaint.status.value,
    }


# --------------------------------------------------
# Administrator: approve subsequent reopening
# --------------------------------------------------

@router.post("/{complaint_id}/reopen/approve")
def approve_reopen_request(
    complaint_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(admin_only),
):
    complaint = _get_complaint(db, complaint_id)

    if complaint.status != Status.CLOSED:
        raise HTTPException(
            409,
            "Only closed complaints can have a reopening request approved",
        )

    pending_request = (
        db.query(AuditLog)
        .filter(
            AuditLog.complaint_id == complaint.id,
            AuditLog.action == "REOPEN_REQUESTED",
            AuditLog.to_value == "Pending Approval",
        )
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
        .first()
    )

    if pending_request is None:
        raise HTTPException(
            404,
            "No pending reopening request found",
        )

    complaint.status = Status.REOPENED

    log_action(
        db,
        action="STATUS_CHANGE",
        complaint_id=complaint.id,
        actor_id=user.id,
        from_value=Status.CLOSED.value,
        to_value=Status.REOPENED.value,
        trigger_type="Administrator Approval",
        reason=(
            f"Approved reopening request. "
            f"Original justification: {pending_request.reason or 'Not provided'}"
        ),
    )

    # Record that the pending request was reviewed.
    log_action(
        db,
        action="REOPEN_APPROVED",
        complaint_id=complaint.id,
        actor_id=user.id,
        from_value="Pending Approval",
        to_value="Approved",
        trigger_type="Administrator",
    )

    db.commit()
    db.refresh(complaint)

    return {
        "message": "Reopening request approved successfully",
        "complaint_id": complaint.id,
        "status": complaint.status.value,
        "approved_by": user.id,
    }
