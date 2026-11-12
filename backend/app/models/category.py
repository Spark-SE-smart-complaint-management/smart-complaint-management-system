from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from app.database import Base
from app.models.enums import Priority


class Category(Base):
    """REQ-12: configurable by the Administrator."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    department = Column(String(50), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class SLAPolicy(Base):
    """REQ-15: SLA duration per category + priority (data-driven, not hard-coded)."""

    __tablename__ = "sla_policies"
    __table_args__ = (UniqueConstraint("category_id", "priority"),)

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    priority = Column(Enum(Priority), nullable=False)
    duration_hours = Column(Integer, nullable=False)
