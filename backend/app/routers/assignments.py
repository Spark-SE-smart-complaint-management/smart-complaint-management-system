"""Complaint assignment: REQ-22 to REQ-25."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Category, Complaint, Notification, Role, Status, User
from app.schemas_assignment import (
    AssignmentOut,
    AutoAssignmentIn,
    ComplaintAssignmentIn,
)
from app.services.audit import log_action

router = APIRouter(prefix="/complaints", tags=["complaint-assignment"])
admin_only = require_role(Role.ADMIN)


def _get_open_complaint(db: Session, complaint_id: int) -> Complaint:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None or complaint.is_archived:
        raise HTTPException(404, "Complaint not found")
    if complaint.status in (Status.RESOLVED, Status.CLOSED):
        raise HTTPException(409, "Resolved or closed complaints cannot be assigned")
    return complaint


def _active_staff(db: Session, staff_id: int) -> User:
    staff = db.get(User, staff_id)
    if staff is None or staff.role != Role.STAFF or not staff.is_active:
        raise HTTPException(422, "Assignee must be an active staff account")
    return staff


def _current_owner(db: Session, complaint: Complaint) -> str | None:
    if complaint.assignee_id is not None:
        staff = db.get(User, complaint.assignee_id)
        return f"user:{staff.id}" if staff else f"user:{complaint.assignee_id}"
    if complaint.assigned_department:
        return f"department:{complaint.assigned_department}"
    return None


def _notify_assignment(
    db: Session, complaint: Complaint, staff: User | None, department: str | None
) -> None:
    """Create durable in-app notification records for the new owner(s)."""
    recipients = (
        [staff]
        if staff
        else (
            db.query(User)
            .filter(
                User.role == Role.STAFF,
                User.is_active.is_(True),
                func.lower(User.department) == department.lower(),
            )
            .all()
        )
    )
    for recipient in recipients:
        db.add(
            Notification(
                user_id=recipient.id,
                event="COMPLAINT_ASSIGNED",
                message=f"Complaint {complaint.reference_id} has been assigned to you.",
                channel="in_app",
                delivery_status="Sent",
            )
        )


def _apply_assignment(
    db: Session,
    complaint: Complaint,
    actor: User,
    *,
    staff: User | None,
    department: str | None,
    reason: str | None,
    automatic: bool = False,
) -> AssignmentOut:
    old_owner = _current_owner(db, complaint)
    new_owner = f"user:{staff.id}" if staff else f"department:{department}"
    if old_owner == new_owner:
        raise HTTPException(409, "Complaint is already assigned to this target")
    if old_owner and not (reason and reason.strip()):
        raise HTTPException(422, "A reason is required when reassigning a complaint")

    complaint.assignee_id = staff.id if staff else None
    complaint.assigned_department = department if staff is None else None
    complaint.status = Status.ASSIGNED

    log_action(
        db,
        action="COMPLAINT_REASSIGNED" if old_owner else "COMPLAINT_ASSIGNED",
        complaint_id=complaint.id,
        actor_id=actor.id,
        from_value=old_owner,
        to_value=new_owner,
        trigger_type="Automatic" if automatic else "Manual",
        reason=reason.strip() if reason else None,
    )
    _notify_assignment(db, complaint, staff, department)
    db.commit()
    db.refresh(complaint)
    return AssignmentOut(
        complaint_id=complaint.id,
        assignee_id=complaint.assignee_id,
        assigned_department=complaint.assigned_department,
        status=complaint.status.value,
        assignment_type="staff" if staff else "department",
        message="Complaint assigned successfully",
    )


@router.post("/{complaint_id}/assign", response_model=AssignmentOut)
def assign_complaint(
    complaint_id: int,
    data: ComplaintAssignmentIn,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    """REQ-22/24/25: manually assign or reassign to one staff member or department."""
    complaint = _get_open_complaint(db, complaint_id)
    staff = _active_staff(db, data.staff_id) if data.staff_id is not None else None
    department = data.department.strip() if data.department else None
    if department:
        exists = (
            db.query(User.id)
            .filter(
                User.role == Role.STAFF,
                User.is_active.is_(True),
                func.lower(User.department) == department.lower(),
            )
            .first()
        )
        if not exists:
            raise HTTPException(
                422, "No active staff members belong to this department"
            )
    return _apply_assignment(
        db, complaint, admin, staff=staff, department=department, reason=data.reason
    )


@router.post("/{complaint_id}/auto-assign", response_model=AssignmentOut)
def auto_assign_complaint(
    complaint_id: int,
    data: AutoAssignmentIn,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    """REQ-23: route by category department, then choose its least-loaded active staff."""
    complaint = _get_open_complaint(db, complaint_id)
    if complaint.category_id is None:
        raise HTTPException(
            422, "Complaint must have a category before auto-assignment"
        )
    category = db.get(Category, complaint.category_id)
    if category is None or not category.is_active or not category.department:
        raise HTTPException(422, "Complaint category has no active department mapping")

    staff_rows = (
        db.query(User)
        .filter(
            User.role == Role.STAFF,
            User.is_active.is_(True),
            func.lower(User.department) == category.department.lower(),
        )
        .order_by(User.id.asc())
        .all()
    )
    if not staff_rows:
        raise HTTPException(
            422, "No active staff members are configured for the category department"
        )

    # Count active assigned work (excluding resolved/closed complaints); stable
    # user-id ordering breaks ties deterministically.
    workload = dict(
        db.query(Complaint.assignee_id, func.count(Complaint.id))
        .filter(
            Complaint.assignee_id.in_([s.id for s in staff_rows]),
            Complaint.status.notin_([Status.RESOLVED, Status.CLOSED]),
            Complaint.is_archived.is_(False),
        )
        .group_by(Complaint.assignee_id)
        .all()
    )
    selected = min(staff_rows, key=lambda s: (workload.get(s.id, 0), s.id))
    reason = (
        data.reason.strip()
        if data.reason and data.reason.strip()
        else (
            f"Automatic assignment: category '{category.name}' mapped to department '{category.department}'; "
            f"selected least-loaded active staff member (workload={workload.get(selected.id, 0)})."
        )
    )
    return _apply_assignment(
        db,
        complaint,
        admin,
        staff=selected,
        department=None,
        reason=reason,
        automatic=True,
    )
