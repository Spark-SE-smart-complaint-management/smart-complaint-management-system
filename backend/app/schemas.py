from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

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


# Issue #3: Complaint submission


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
    assignee_id: int | None
    assigned_department: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# Issue #5: Complaint status and history


class ComplaintStatusUpdateIn(BaseModel):
    status: Status
    reason: str | None = Field(default=None, max_length=500)


class ComplaintHistoryOut(BaseModel):
    id: int
    complaint_id: int
    actor_id: int | None
    action: str
    from_value: str | None
    to_value: str | None
    trigger_type: str | None
    reason: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}


# Issue #10: Complaint comments


class CommentCreateIn(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class CommentOut(BaseModel):
    id: int
    complaint_id: int
    author_id: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationPreferenceIn(BaseModel):
    channels: list[str] = Field(min_length=1, max_length=3)

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, value):
        allowed = {"in_app", "email", "sms"}
        if len(set(value)) != len(value):
            raise ValueError("Notification channels must be unique")
        if any(channel not in allowed for channel in value):
            raise ValueError("Channels must be in_app, email, or sms")
        return value


class NotificationPreferenceOut(BaseModel):
    channels: list[str]


class NotificationOut(BaseModel):
    id: int
    event: str
    message: str
    channel: str
    delivery_status: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationDeliveryOut(BaseModel):
    id: int
    notification_id: int
    channel: str
    delivery_status: str
    attempts: int
    last_error: str | None
    next_attempt_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
