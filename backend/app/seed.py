"""Create a first admin:  python -m app.seed"""
from app.database import Base, SessionLocal, engine
from app.models import Role, User
from app.security import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()
if not db.query(User).filter(User.email == "admin@example.com").first():
    db.add(User(name="Admin", email="admin@example.com",
                password_hash=hash_password("Admin@12345"), role=Role.ADMIN))
    db.commit()
    print("Created admin@example.com / Admin@12345")
else:
    print("Admin already exists")
