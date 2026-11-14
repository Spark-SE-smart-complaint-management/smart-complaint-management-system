from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import (
    Category,
    Complaint,
    EscalationHierarchy,
    Role,
    Status,
    User,
)
from app.schemas_escalation import (
    EscalationHierarchyIn,
    EscalationHierarchyOut,
)
from app.services.audit import log_action
from app.services.escalation import escalate_complaint


router = APIRouter(
    prefix="/escalation-hierarchy",
    tags=["SLA escalation"],
)

admin_only = require_role(Role.ADMIN)


# --------------------------------------------------
# Manual escalation request schema (REQ-29)
# --------------------------------------------------

class ManualEscalationIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


# --------------------------------------------------
# Validate escalation configuration
# --------------------------------------------------

def _validate_configuration(db: Session, data):

    category = None

    if data.category_id is not None:
        category = db.get(Category, data.category_id)

        if category is None or not category.is_active:
            raise HTTPException(422, "Active category not found")

        if data.assignee_id is None:
            raise HTTPException(
                422,
                "Category-specific escalation levels require an assignee",
            )

    if data.department is not None:

        exists = (
            db.query(User.id)
            .filter(
                User.role == Role.STAFF,
                User.is_active.is_(True),
                func.lower(User.department) == data.department.lower(),
            )
            .first()
        )

        if not exists:
            raise HTTPException(
                422,
                "No active staff members exist in this department",
            )

    if data.assignee_id is not None:

        staff = db.get(User, data.assignee_id)

        if (
            staff is None
            or staff.role != Role.STAFF
            or not staff.is_active
        ):
            raise HTTPException(
                422,
                "Assignee must be an active staff account",
            )

        expected_department = (
            data.department
            if data.department is not None
            else category.department
        )

        if (
            expected_department
            and (
                not staff.department
                or staff.department.lower() != expected_department.lower()
            )
        ):
            raise HTTPException(
                422,
                "Assignee must belong to the configured department",
            )


# --------------------------------------------------
# Check duplicate escalation level
# --------------------------------------------------

def _duplicate_level(db: Session, data, exclude_id=None):

    query = db.query(EscalationHierarchy).filter(
        EscalationHierarchy.level == data.level
    )

    if data.category_id is not None:
        query = query.filter(
            EscalationHierarchy.category_id == data.category_id,
            EscalationHierarchy.department.is_(None),
        )
    else:
        query = query.filter(
            EscalationHierarchy.department == data.department,
            EscalationHierarchy.category_id.is_(None),
        )

    if exclude_id is not None:
        query = query.filter(
            EscalationHierarchy.id != exclude_id
        )

    return query.first() is not None


# --------------------------------------------------
# Create escalation level (REQ-26)
# --------------------------------------------------

@router.post(
    "",
    response_model=EscalationHierarchyOut,
    status_code=201,
)
def create_escalation_level(
    data: EscalationHierarchyIn,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):

    _validate_configuration(db, data)

    if _duplicate_level(db, data):
        raise HTTPException(
            409,
            "This escalation level already exists",
        )

    level = EscalationHierarchy(**data.model_dump())

    db.add(level)
    db.flush()

    log_action(
        db,
        action="ESCALATION_HIERARCHY_CREATE",
        actor_id=admin.id,
        to_value=str(data.model_dump()),
        trigger_type="Manual",
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409,
            "Duplicate escalation hierarchy level",
        )

    db.refresh(level)
    return level


# --------------------------------------------------
# List escalation levels
# --------------------------------------------------

@router.get(
    "",
    response_model=list[EscalationHierarchyOut],
)
def list_escalation_levels(
    category_id: int | None = None,
    department: str | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):

    if category_id is not None and department is not None:
        raise HTTPException(
            422,
            "Filter by category or department, not both",
        )

    query = db.query(EscalationHierarchy)

    if category_id is not None:
        query = query.filter(
            EscalationHierarchy.category_id == category_id
        )

    if department is not None:
        query = query.filter(
            func.lower(EscalationHierarchy.department)
            == department.lower()
        )

    return query.order_by(
        EscalationHierarchy.level.asc()
    ).all()


# --------------------------------------------------
# Update escalation level
# --------------------------------------------------

@router.put(
    "/{hierarchy_id}",
    response_model=EscalationHierarchyOut,
)
def update_escalation_level(
    hierarchy_id: int,
    data: EscalationHierarchyIn,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):

    level = db.get(EscalationHierarchy, hierarchy_id)

    if level is None:
        raise HTTPException(404, "Escalation level not found")

    _validate_configuration(db, data)

    if _duplicate_level(db, data, exclude_id=hierarchy_id):
        raise HTTPException(
            409,
            "This escalation level already exists",
        )

    old_value = {
        "category_id": level.category_id,
        "department": level.department,
        "level": level.level,
        "assignee_id": level.assignee_id,
        "role_name": level.role_name,
        "is_active": level.is_active,
    }

    for field, value in data.model_dump().items():
        setattr(level, field, value)

    log_action(
        db,
        action="ESCALATION_HIERARCHY_UPDATE",
        actor_id=admin.id,
        from_value=str(old_value),
        to_value=str(data.model_dump()),
        trigger_type="Manual",
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409,
            "Duplicate escalation hierarchy level",
        )

    db.refresh(level)
    return level


# --------------------------------------------------
# Deactivate escalation level
# --------------------------------------------------

@router.delete("/{hierarchy_id}", status_code=204)
def deactivate_escalation_level(
    hierarchy_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):

    level = db.get(EscalationHierarchy, hierarchy_id)

    if level is None:
        raise HTTPException(404, "Escalation level not found")

    old_value = str(level.is_active)
    level.is_active = False

    log_action(
        db,
        action="ESCALATION_HIERARCHY_DEACTIVATE",
        actor_id=admin.id,
        from_value=old_value,
        to_value="False",
        trigger_type="Manual",
    )

    db.commit()


# --------------------------------------------------
# Manual complaint escalation (REQ-29)
# --------------------------------------------------

@router.post("/complaints/{complaint_id}/manual")
def manual_escalation(
    complaint_id: int,
    data: ManualEscalationIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(Role.STAFF, Role.ADMIN)),
):

    complaint = db.get(Complaint, complaint_id)

    if complaint is None or complaint.is_archived:
        raise HTTPException(404, "Complaint not found")

    if complaint.status in (Status.RESOLVED, Status.CLOSED):
        raise HTTPException(
            409,
            "Resolved complaints cannot be escalated",
        )

    reason = data.reason.strip()

    if not reason:
        raise HTTPException(
            422,
            "Escalation reason is required",
        )

    success = escalate_complaint(
        db,
        complaint,
        actor_id=actor.id,
        reason=reason,
        trigger_type="Manual",
    )

    if not success:
        raise HTTPException(
            409,
            "No eligible next escalation level is configured",
        )

    db.commit()

    return {
        "message": "Complaint escalated successfully",
        "complaint_id": complaint.id,
        "escalation_level": complaint.escalation_level,
        "status": complaint.status,
    }