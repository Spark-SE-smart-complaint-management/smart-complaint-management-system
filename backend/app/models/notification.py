from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)

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
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )


class NotificationPreference(Base):
    """Per-user channel preferences. The default is always the in-app inbox."""

    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    channels = Column(Text, nullable=False, default='["in_app"]')
    updated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )


class NotificationDelivery(Base):
    """Transactional outbox and durable delivery/retry log for REQ-42."""

    __tablename__ = "notification_deliveries"
    __table_args__ = (
        Index("ix_notification_deliveries_due", "delivery_status", "next_attempt_at"),
    )

    id = Column(Integer, primary_key=True)
    notification_id = Column(
        Integer, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False
    )
    channel = Column(String(10), nullable=False)
    idempotency_key = Column(String(64), nullable=False, unique=True)
    delivery_status = Column(String(15), nullable=False, default="Pending")
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    next_attempt_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
