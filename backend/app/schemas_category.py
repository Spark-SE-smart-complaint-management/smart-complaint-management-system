"""Schemas for issue #4 (categories, priority, SLA policy). Kept separate from schemas.py to avoid merge conflicts."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import Priority, SLAStatus, Status


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    department: str | None = Field(default=None, max_length=50)


class CategoryUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    department: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    department: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class SuggestIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class SuggestOut(BaseModel):
    category: CategoryOut | None


class SLAPolicyIn(BaseModel):
    category_id: int
    priority: Priority
    duration_hours: int = Field(gt=0, le=8760)


class SLAPolicyOut(BaseModel):
    id: int
    category_id: int
    priority: Priority
    duration_hours: int

    model_config = {"from_attributes": True}


class PriorityIn(BaseModel):
    priority: Priority


class CategoryChangeIn(BaseModel):
    category_id: int


class TriageOut(BaseModel):
    id: int
    reference_id: str
    status: Status
    category_id: int | None
    priority: Priority | None
    sla_deadline: datetime | None
    sla_status: SLAStatus | None

    model_config = {"from_attributes": True}