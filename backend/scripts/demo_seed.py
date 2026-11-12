"""Seed a repeatable demo with synthetic users and complaints only.

Requires DEMO_PASSWORD. Run only against an isolated development database.
"""

import os
from datetime import UTC, datetime, timedelta

from app.database import Base, SessionLocal, engine
from app.models import (
    Category,
    Complaint,
    Priority,
    Role,
    SLAStatus,
    Status,
    User,
)
from app.security import hash_password, validate_password_strength
from app.services.audit import log_action

DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "")
if not DEMO_PASSWORD:
    raise SystemExit("Set DEMO_PASSWORD to a strong local-only password")
problems = validate_password_strength(DEMO_PASSWORD)
if problems:
    raise SystemExit("DEMO_PASSWORD must contain " + ", ".join(problems))

Base.metadata.create_all(bind=engine)
db = SessionLocal()


def ensure_user(name: str, email: str, role: Role, department: str | None = None):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        if existing.role != role:
            raise SystemExit(f"Existing demo account {email} has a different role")
        return existing
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(DEMO_PASSWORD),
        role=role,
        department=department,
    )
    db.add(user)
    db.flush()
    return user


try:
    ensure_user("Demo Administrator", "demo.admin@example.com", Role.ADMIN)
    staff = ensure_user(
        "Demo Agent", "demo.staff@example.com", Role.STAFF, "IT Support"
    )
    citizen = ensure_user("Demo Citizen", "demo.citizen@example.com", Role.COMPLAINANT)
    category = db.query(Category).filter(Category.name == "Technical").first()
    if category is None:
        category = Category(name="Technical", department="IT Support", is_active=True)
        db.add(category)
        db.flush()

    now = datetime.now(UTC).replace(tzinfo=None)
    records = [
        (
            "CMP-2026-900001",
            "Demo: new request",
            Status.NEW,
            None,
            now - timedelta(hours=1),
        ),
        (
            "CMP-2026-900002",
            "Demo: assigned request",
            Status.IN_PROGRESS,
            staff.id,
            now - timedelta(hours=6),
        ),
        (
            "CMP-2026-900003",
            "Demo: resolved request",
            Status.RESOLVED,
            staff.id,
            now - timedelta(days=1),
        ),
    ]
    for reference_id, title, status, assignee_id, created_at in records:
        if db.query(Complaint).filter(Complaint.reference_id == reference_id).first():
            continue
        complaint = Complaint(
            reference_id=reference_id,
            complainant_id=citizen.id,
            title=title,
            description="Synthetic demo data. No real person or incident is represented.",
            category_id=category.id,
            priority=Priority.MEDIUM,
            status=status,
            assignee_id=assignee_id,
            created_at=created_at,
            sla_deadline=created_at + timedelta(hours=12),
            sla_status=SLAStatus.ON_TRACK,
        )
        db.add(complaint)
        db.flush()
        if status == Status.RESOLVED:
            log_action(
                db,
                action="STATUS_CHANGE",
                complaint_id=complaint.id,
                actor_id=staff.id,
                from_value=Status.IN_PROGRESS.value,
                to_value=Status.RESOLVED.value,
                trigger_type="Demo seed",
            )
        db.flush()
    db.commit()
    print(
        "Demo accounts: demo.admin@example.com, demo.staff@example.com, demo.citizen@example.com"
    )
    print(
        "All demo accounts use DEMO_PASSWORD. Complaint references CMP-2026-900001–900003."
    )
finally:
    db.close()
