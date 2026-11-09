"""Issue #4: set category / priority on a complaint (REQ-13, 14, 16)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Category, Complaint, Role, Status, User
from app.schemas_category import CategoryChangeIn, PriorityIn, SuggestOut, TriageOut
from app.services.audit import log_action
from app.services.categorizer import suggest_category
from app.services.sla import recompute_sla

router = APIRouter(prefix="/complaints", tags=["triage"])
staff_or_admin = require_role(Role.STAFF, Role.ADMIN)


def _load(db: Session, complaint_id: int, user: User) -> Complaint:
    c = db.get(Complaint, complaint_id)
    if not c:
        raise HTTPException(404, "Complaint not found")
    # Staff may triage unassigned complaints or their own; Admin may triage any (SRS 6.5).
    if user.role == Role.STAFF and c.assignee_id not in (None, user.id):
        raise HTTPException(403, "Complaint is assigned to another staff member")
    return c


def _ensure_open(c: Complaint) -> None:
    if c.status == Status.CLOSED:
        raise HTTPException(409, "Closed complaints cannot be re-triaged")


@router.get("/{complaint_id}/suggested-category", response_model=SuggestOut)
def suggested_category(complaint_id: int, db: Session = Depends(get_db), user: User = Depends(staff_or_admin)):
    c = _load(db, complaint_id, user)
    return SuggestOut(category=suggest_category(db, f"{c.title} {c.description}"))


@router.patch("/{complaint_id}/category", response_model=TriageOut)
def set_category(complaint_id: int, data: CategoryChangeIn, db: Session = Depends(get_db),
                 user: User = Depends(staff_or_admin)):
    c = _load(db, complaint_id, user)
    _ensure_open(c)
    cat = db.get(Category, data.category_id)
    if not cat:
        raise HTTPException(404, "Category not found")
    if not cat.is_active:
        raise HTTPException(422, "Category is inactive")
    old = db.get(Category, c.category_id) if c.category_id else None
    c.category_id = cat.id
    log_action(db, action="CATEGORY_CHANGE", complaint_id=c.id, actor_id=user.id,
               from_value=old.name if old else None, to_value=cat.name, trigger_type="Manual")
    recompute_sla(db, c, actor_id=user.id)  # REQ-16
    db.commit()
    db.refresh(c)
    return c


@router.patch("/{complaint_id}/priority", response_model=TriageOut)
def set_priority(complaint_id: int, data: PriorityIn, db: Session = Depends(get_db),
                 user: User = Depends(staff_or_admin)):
    c = _load(db, complaint_id, user)
    _ensure_open(c)
    old = c.priority.value if c.priority else None
    c.priority = data.priority
    log_action(db, action="PRIORITY_CHANGE", complaint_id=c.id, actor_id=user.id,
               from_value=old, to_value=data.priority.value, trigger_type="Manual")
    recompute_sla(db, c, actor_id=user.id)  # REQ-16
    db.commit()
    db.refresh(c)
    return c