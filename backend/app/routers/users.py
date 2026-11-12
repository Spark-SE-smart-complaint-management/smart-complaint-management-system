from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Role, User
from app.routers.auth import create_user
from app.schemas import AdminCreateUserIn, AdminUpdateUserIn, UserOut

router = APIRouter(
    prefix="/users", tags=["users"], dependencies=[Depends(require_role(Role.ADMIN))]
)


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.post("", response_model=UserOut, status_code=201)
def admin_create_user(data: AdminCreateUserIn, db: Session = Depends(get_db)):
    return create_user(db, data, data.role, data.department)  # REQ-5


@router.patch("/{user_id}", response_model=UserOut)
def admin_update_user(
    user_id: int, data: AdminUpdateUserIn, db: Session = Depends(get_db)
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)  # change role / deactivate (REQ-5)
    db.commit()
    db.refresh(user)
    return user
