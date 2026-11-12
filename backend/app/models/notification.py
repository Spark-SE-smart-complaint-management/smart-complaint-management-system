from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class Notification(Base):
    """REQ-42: log of every notification with delivery status."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(
        String(10), nullable=False, default="in_app"
    )  # in_app / email / sms
    delivery_status = Column(String(15), nullable=False, default="Sent")
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
