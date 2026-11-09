from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class AuditLog(Base):
    """REQ-19 / REQ-30: append-only trail. Never update or delete rows."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = system/scheduler
    action = Column(String(50), nullable=False)   # STATUS_CHANGE, ASSIGN, ESCALATE ...
    from_value = Column(String(100), nullable=True)
    to_value = Column(String(100), nullable=True)
    trigger_type = Column(String(30), nullable=True)  # Manual / Automatic
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
