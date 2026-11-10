from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models import Priority, Role, Status


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=15)
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None
    role: Role
    department: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class AdminCreateUserIn(RegisterIn):
    role: Role
    department: str | None = Field(default=None, max_length=50)


class AdminUpdateUserIn(BaseModel):
    role: Role | None = None
    is_active: bool | None = None
    department: str | None = Field(default=None, max_length=50)





class ComplaintCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=2000)
    category_id: int | None = None


class ComplaintOut(BaseModel):
    id: int
    reference_id: str
    complainant_id: int
    title: str
    description: str
    category_id: int | None
    priority: Priority | None
    status: Status
    created_at: datetime

    model_config = {"from_attributes": True}
