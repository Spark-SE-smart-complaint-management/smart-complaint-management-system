from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Role, User
from app.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.security import (create_access_token, hash_password,
                          validate_password_strength, verify_password)

router = APIRouter(prefix="/auth", tags=["auth"])


def create_user(db: Session, data: RegisterIn, role: Role, department: str | None = None) -> User:
    email = data.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")  # REQ-2
    problems = validate_password_strength(data.password)
    if problems:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Weak password. Needs: " + ", ".join(problems),
        )
    user = User(name=data.name, email=email, phone=data.phone,
                password_hash=hash_password(data.password), role=role, department=department)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    # Public sign-up always creates a Complainant; staff/admin are created by an Administrator (REQ-5)
    return create_user(db, data, Role.COMPLAINANT)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.password_hash) or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenOut(access_token=create_access_token(user.id, user.role.value))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
