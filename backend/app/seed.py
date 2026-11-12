"""Seed the first admin + defaults. Requires ADMIN_PASSWORD to be set."""

import os

from app.database import Base, SessionLocal, engine
from app.models import Category, Priority, Role, SLAPolicy, User
from app.security import hash_password, validate_password_strength

# name -> (department, {priority: SLA hours})
DEFAULTS = {
    "Billing": (
        "Finance",
        {
            Priority.CRITICAL: 8,
            Priority.HIGH: 24,
            Priority.MEDIUM: 48,
            Priority.LOW: 96,
        },
    ),
    "Technical": (
        "IT Support",
        {Priority.CRITICAL: 2, Priority.HIGH: 4, Priority.MEDIUM: 12, Priority.LOW: 48},
    ),
    "Service Quality": (
        "Customer Service",
        {
            Priority.CRITICAL: 4,
            Priority.HIGH: 12,
            Priority.MEDIUM: 48,
            Priority.LOW: 96,
        },
    ),
    "Staff Behaviour": (
        "HR",
        {Priority.CRITICAL: 4, Priority.HIGH: 8, Priority.MEDIUM: 24, Priority.LOW: 72},
    ),
}

Base.metadata.create_all(bind=engine)
db = SessionLocal()

admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com").strip().lower()
admin_password = os.getenv("ADMIN_PASSWORD")
if not admin_password:
    raise SystemExit("Set ADMIN_PASSWORD before running the seed command")
password_problems = validate_password_strength(admin_password)
if password_problems:
    raise SystemExit("ADMIN_PASSWORD must contain " + ", ".join(password_problems))

if not db.query(User).filter(User.email == admin_email).first():
    db.add(
        User(
            name="Admin",
            email=admin_email,
            password_hash=hash_password(admin_password),
            role=Role.ADMIN,
        )
    )
    db.commit()
    print("Created administrator account")
else:
    print("Administrator account already exists")

for name, (dept, matrix) in DEFAULTS.items():
    cat = db.query(Category).filter(Category.name == name).first()
    if not cat:
        cat = Category(name=name, department=dept)
        db.add(cat)
        db.flush()
        print(f"Created category {name}")
    for prio, hours in matrix.items():
        exists = (
            db.query(SLAPolicy)
            .filter(SLAPolicy.category_id == cat.id, SLAPolicy.priority == prio)
            .first()
        )
        if not exists:
            db.add(SLAPolicy(category_id=cat.id, priority=prio, duration_hours=hours))
db.commit()
print("Seed complete")
