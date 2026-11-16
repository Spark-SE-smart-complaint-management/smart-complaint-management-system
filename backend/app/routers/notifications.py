"""User notification inbox/preferences and administrator delivery controls."""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    Role,
    User,
)
from app.schemas import (
    NotificationDeliveryOut,
    NotificationHistoryOut,
    NotificationOut,
    NotificationPreferenceIn,
    NotificationPreferenceOut,
)
from app.services.notify import retry_failed

router = APIRouter(prefix="/notifications", tags=["notifications"])
admin_only = require_role(Role.ADMIN)


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.channel == "in_app")
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    notification = db.get(Notification, notification_id)
    if (
        notification is None
        or notification.user_id != user.id
        or notification.channel != "in_app"
    ):
        raise HTTPException(404, "Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.patch("/read-all")
def mark_all_read(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    changed = (
        db.query(Notification)
        .filter(
            Notification.user_id == user.id,
            Notification.channel == "in_app",
            Notification.is_read.is_(False),
        )
        .update({Notification.is_read: True}, synchronize_session=False)
    )
    db.commit()
    return {"updated": int(changed)}


@router.get("/preferences", response_model=NotificationPreferenceOut)
def get_preferences(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    preference = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user.id)
        .first()
    )
    channels = json.loads(preference.channels) if preference else ["in_app"]
    return {"channels": channels}


@router.put("/preferences", response_model=NotificationPreferenceOut)
def set_preferences(
    data: NotificationPreferenceIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    preference = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user.id)
        .first()
    )
    if preference is None:
        preference = NotificationPreference(user_id=user.id)
        db.add(preference)
    preference.channels = json.dumps(data.channels, separators=(",", ":"))
    preference.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return {"channels": data.channels}


@router.get("/history", response_model=list[NotificationHistoryOut])
def list_notification_history(
    event: str | None = Query(default=None, min_length=1, max_length=50),
    user_id: int | None = Query(default=None, ge=1),
    channel: str | None = Query(default=None, pattern="^(in_app|email|sms)$"),
    status: str | None = Query(default=None, pattern="^(Pending|Sent|Failed)$"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    """Return searchable delivery audit metadata for administrators.

    Message bodies and recipient contact details are deliberately excluded.
    """
    query = (
        db.query(Notification, NotificationDelivery)
        .join(
            NotificationDelivery,
            NotificationDelivery.notification_id == Notification.id,
        )
    )
    if event:
        query = query.filter(Notification.event == event)
    if user_id is not None:
        query = query.filter(Notification.user_id == user_id)
    if channel:
        query = query.filter(NotificationDelivery.channel == channel)
    if status:
        query = query.filter(NotificationDelivery.delivery_status == status)
    rows = (
        query.order_by(
            Notification.created_at.desc(),
            Notification.id.desc(),
            NotificationDelivery.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": notification.id,
            "user_id": notification.user_id,
            "event": notification.event,
            "channel": delivery.channel,
            "delivery_status": delivery.delivery_status,
            "is_read": notification.is_read,
            "attempts": delivery.attempts,
            "last_error": delivery.last_error,
            "next_attempt_at": delivery.next_attempt_at,
            "created_at": notification.created_at,
        }
        for notification, delivery in rows
    ]

@router.get("/deliveries", response_model=list[NotificationDeliveryOut])
def list_delivery_log(
    status: str | None = Query(default=None, pattern="^(Pending|Sent|Failed)$"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    query = db.query(NotificationDelivery)
    if status:
        query = query.filter(NotificationDelivery.delivery_status == status)
    return (
        query.order_by(
            NotificationDelivery.created_at.desc(), NotificationDelivery.id.desc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("/retry-failed")
def retry_delivery_failures(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    return retry_failed(db, limit=limit)
