"""Seed admin + default categories + default SLA matrix:  python -m app.seed  (safe to re-run)"""
from app.database import Base, SessionLocal, engine
from app.models import Category, Priority, Role, SLAPolicy, User
from app.security import hash_password

# name -> (department, {priority: SLA hours})
DEFAULTS = {
    "Billing": ("Finance", {Priority.CRITICAL: 8, Priority.HIGH: 24, Priority.MEDIUM: 48, Priority.LOW: 96}),
    "Technical": ("IT Support", {Priority.CRITICAL: 2, Priority.HIGH: 4, Priority.MEDIUM: 12, Priority.LOW: 48}),
    "Service Quality": ("Customer Service", {Priority.CRITICAL: 4, Priority.HIGH: 12, Priority.MEDIUM: 48, Priority.LOW: 96}),
    "Staff Behaviour": ("HR", {Priority.CRITICAL: 4, Priority.HIGH: 8, Priority.MEDIUM: 24, Priority.LOW: 72}),
}

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if not db.query(User).filter(User.email == "admin@example.com").first():
    db.add(User(name="Admin", email="admin@example.com",
                password_hash=hash_password("Admin@12345"), role=Role.ADMIN))
    db.commit()
    print("Created admin@example.com / Admin@12345")
else:
    print("Admin already exists")

for name, (dept, matrix) in DEFAULTS.items():
    cat = db.query(Category).filter(Category.name == name).first()
    if not cat:
        cat = Category(name=name, department=dept)
        db.add(cat)
        db.flush()
        print(f"Created category {name}")
    for prio, hours in matrix.items():
        exists = db.query(SLAPolicy).filter(SLAPolicy.category_id == cat.id, SLAPolicy.priority == prio).first()
        if not exists:
            db.add(SLAPolicy(category_id=cat.id, priority=prio, duration_hours=hours))
db.commit()
print("Seed complete")