from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.database import Base
from app.models.enums import Priority, SLAStatus, Status


class Complaint(Base):
    """Fields follow SRS Appendix B.1, plus SLA and assignment bookkeeping."""

    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True)
    reference_id = Column(String(16), unique=True, nullable=False, index=True)
    complainant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(String(2000), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    priority = Column(Enum(Priority), nullable=True)
    status = Column(Enum(Status), nullable=False, default=Status.NEW)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Department-level assignment is mutually exclusive with assignee_id.
    assigned_department = Column(String(50), nullable=True, index=True)
    attachment_urls = Column(Text, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # SLA / escalation bookkeeping (used by issues #4, #7, #8)
    sla_deadline = Column(DateTime, nullable=True)
    sla_status = Column(Enum(SLAStatus), nullable=True)
    sla_warning_sent = Column(Boolean, nullable=False, default=False)
    escalation_level = Column(Integer, nullable=False, default=0)
    sla_paused_at = Column(DateTime, nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False)
