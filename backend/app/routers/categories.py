"""Issue #4: categories (REQ-12), keyword suggestion (REQ-13), SLA policies (REQ-15)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import Category, Role, SLAPolicy, User
from app.schemas_category import (
    CategoryIn, CategoryOut, CategoryUpdateIn, SLAPolicyIn, SLAPolicyOut, SuggestIn, SuggestOut,
)
from app.services.audit import log_action
from app.services.categorizer import suggest_category

router = APIRouter(tags=["categories & SLA policy"])
admin_only = require_role(Role.ADMIN)


def _name_taken(db: Session, name: str, exclude_id: int | None = None) -> bool:
    q = db.query(Category).filter(func.lower(Category.name) == name.lower())
    if exclude_id is not None:
        q = q.filter(Category.id != exclude_id)
    return q.first() is not None


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(include_inactive: bool = False, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    q = db.query(Category)
    if not (include_inactive and user.role == Role.ADMIN):
        q = q.filter(Category.is_active.is_(True))
    return q.order_by(Category.name).all()


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(data: CategoryIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    name = data.name.strip()
    if not name:
        raise HTTPException(422, "Category name cannot be blank")
    if _name_taken(db, name):
        raise HTTPException(409, "Category already exists")
    cat = Category(name=name, department=data.department)
    db.add(cat)
    db.flush()
    log_action(db, action="CATEGORY_CREATE", actor_id=admin.id, to_value=name, trigger_type="Manual")
    db.commit()
    db.refresh(cat)
    return cat


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, data: CategoryUpdateIn, db: Session = Depends(get_db),
                    admin: User = Depends(admin_only)):
    cat = db.get(Category, category_id)
    if not cat:
        raise HTTPException(404, "Category not found")
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        if not changes["name"]:
            raise HTTPException(422, "Category name cannot be blank")
        if _name_taken(db, changes["name"], exclude_id=cat.id):
            raise HTTPException(409, "Category already exists")
    for field, value in changes.items():
        setattr(cat, field, value)
    log_action(db, action="CATEGORY_UPDATE", actor_id=admin.id, to_value=str(changes), trigger_type="Manual")
    db.commit()
    db.refresh(cat)
    return cat


@router.post("/categories/suggest", response_model=SuggestOut)
def suggest(data: SuggestIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """REQ-13: suggestion for the Lodge Complaint form. Nothing is saved."""
    return SuggestOut(category=suggest_category(db, data.text))


# ---- SLA policies (REQ-15) -------------------------------------------------

@router.get("/sla-policies", response_model=list[SLAPolicyOut])
def list_sla_policies(category_id: int | None = None, db: Session = Depends(get_db),
                      user: User = Depends(require_role(Role.STAFF, Role.ADMIN))):
    q = db.query(SLAPolicy)
    if category_id is not None:
        q = q.filter(SLAPolicy.category_id == category_id)
    return q.order_by(SLAPolicy.category_id, SLAPolicy.id).all()


@router.put("/sla-policies", response_model=SLAPolicyOut)
def upsert_sla_policy(data: SLAPolicyIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    """Create or update the SLA duration for one category + priority (no code change needed)."""
    if not db.get(Category, data.category_id):
        raise HTTPException(404, "Category not found")
    policy = (
        db.query(SLAPolicy)
        .filter(SLAPolicy.category_id == data.category_id, SLAPolicy.priority == data.priority)
        .first()
    )
    old = policy.duration_hours if policy else None
    if policy:
        policy.duration_hours = data.duration_hours
    else:
        policy = SLAPolicy(category_id=data.category_id, priority=data.priority,
                           duration_hours=data.duration_hours)
        db.add(policy)
    log_action(db, action="SLA_POLICY_SET", actor_id=admin.id,
               from_value=str(old) if old is not None else None, to_value=str(data.duration_hours),
               trigger_type="Manual", reason=f"category_id={data.category_id}, priority={data.priority.value}")
    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/sla-policies/{policy_id}", status_code=204)
def delete_sla_policy(policy_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    policy = db.get(SLAPolicy, policy_id)
    if not policy:
        raise HTTPException(404, "SLA policy not found")
    log_action(db, action="SLA_POLICY_DELETE", actor_id=admin.id, from_value=str(policy.duration_hours),
               trigger_type="Manual", reason=f"category_id={policy.category_id}, priority={policy.priority.value}")
    db.delete(policy)
    db.commit()
