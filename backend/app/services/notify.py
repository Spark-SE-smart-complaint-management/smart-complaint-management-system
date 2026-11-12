"""Idempotent notification inbox and retryable delivery outbox (REQ-39 to REQ-42)."""

import hashlib
import json
import os
import smtplib
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    User,
)

CHANNELS = {"in_app", "email", "sms"}
MAX_ATTEMPTS = 8


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _stable_key(user_id: int, event: str, message: str, channel: str, key: str | None):
    source = key or f"{event}:{message}"
    value = f"{user_id}:{channel}:{source}".encode()
    return hashlib.sha256(value).hexdigest()


def _preferred_channels(db: Session, user_id: int) -> list[str]:
    preference = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user_id)
        .first()
    )
    if preference is None:
        return ["in_app"]
    try:
        channels = json.loads(preference.channels)
    except (TypeError, ValueError):
        return ["in_app"]
    if not isinstance(channels, list) or not channels:
        return ["in_app"]
    return [channel for channel in channels if channel in CHANNELS] or ["in_app"]


def notify(
    db: Session,
    user_id: int,
    event: str,
    message: str,
    channel: str | None = None,
    *,
    idempotency_key: str | None = None,
) -> list[Notification]:
    """Queue one notification per preferred channel; caller owns the transaction.

    In-app entries are durable immediately within the caller's transaction. External
    channels remain in the outbox until ``dispatch_pending`` runs after commit.
    """
    if channel is not None and channel not in CHANNELS:
        raise ValueError(f"Unsupported notification channel: {channel}")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return []
    channels = [channel] if channel else _preferred_channels(db, user_id)
    created: list[Notification] = []
    for selected_channel in channels:
        key = _stable_key(user_id, event, message, selected_channel, idempotency_key)
        existing = (
            db.query(NotificationDelivery)
            .filter(NotificationDelivery.idempotency_key == key)
            .first()
        )
        if existing is not None:
            notification = db.get(Notification, existing.notification_id)
            if notification is not None:
                created.append(notification)
            continue
        status = "Sent" if selected_channel == "in_app" else "Pending"
        try:
            with db.begin_nested():
                row = Notification(
                    user_id=user_id,
                    event=event,
                    message=message,
                    channel=selected_channel,
                    delivery_status=status,
                )
                db.add(row)
                db.flush()
                delivery = NotificationDelivery(
                    notification_id=row.id,
                    channel=selected_channel,
                    idempotency_key=key,
                    delivery_status=status,
                    attempts=0,
                    created_at=_now(),
                    updated_at=_now(),
                )
                db.add(delivery)
                db.flush()
                created.append(row)
        except IntegrityError:
            # The unique key protects concurrent event handlers; retain the existing row.
            existing = (
                db.query(NotificationDelivery)
                .filter(NotificationDelivery.idempotency_key == key)
                .first()
            )
            if existing is not None:
                row = db.get(Notification, existing.notification_id)
                if row is not None:
                    created.append(row)
    return created


def notify_sla_at_risk(
    db: Session,
    *,
    complaint_id: int,
    reference_id: str,
    recipient_id: int,
    event_id: str,
) -> list[Notification]:
    """Stable hook for the SLA scheduler's pre-breach warning (REQ-28)."""
    return notify(
        db,
        recipient_id,
        "SLA_AT_RISK",
        f"Complaint {reference_id} is approaching its SLA deadline.",
        idempotency_key=f"complaint:{complaint_id}:sla-warning:{event_id}",
    )


def notify_escalation(
    db: Session,
    *,
    complaint_id: int,
    reference_id: str,
    recipient_ids: list[int],
    event_id: str,
) -> list[Notification]:
    """Stable hook for escalation recipients (REQ-27/30); duplicate-safe per event."""
    created: list[Notification] = []
    for recipient_id in sorted(set(recipient_ids)):
        created.extend(
            notify(
                db,
                recipient_id,
                "COMPLAINT_ESCALATED",
                f"Complaint {reference_id} has been escalated.",
                idempotency_key=f"complaint:{complaint_id}:escalation:{event_id}",
            )
        )
    return created


def _send_email(user: User, notification: Notification, delivery: NotificationDelivery):
    host = os.getenv("SMTP_HOST", "").strip()
    sender = os.getenv("SMTP_SENDER", "").strip()
    if not host or not sender:
        raise RuntimeError("Email delivery is not configured (SMTP_HOST/SMTP_SENDER)")
    message = EmailMessage()
    message["To"] = user.email
    message["From"] = sender
    message["Subject"] = (
        f"Complaint update: {notification.event.replace('_', ' ').title()}"
    )
    message["Message-ID"] = f"<{delivery.idempotency_key}@smart-complaint.local>"
    message.set_content(notification.message)
    port = int(os.getenv("SMTP_PORT", "587"))
    timeout = float(os.getenv("SMTP_TIMEOUT_SECONDS", "10"))
    username = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    if os.getenv("SMTP_USE_SSL", "false").lower() == "true":
        with smtplib.SMTP_SSL(
            host, port, timeout=timeout, context=ssl.create_default_context()
        ) as smtp:
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=timeout) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if username:
                smtp.login(username, password)
            smtp.send_message(message)


def _send_sms(user: User, notification: Notification, delivery: NotificationDelivery):
    endpoint = os.getenv("SMS_WEBHOOK_URL", "").strip()
    if not endpoint:
        raise RuntimeError("SMS delivery is not configured (SMS_WEBHOOK_URL)")
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("SMS_WEBHOOK_URL must use HTTPS")
    if not user.phone:
        raise RuntimeError("User has no phone number for SMS delivery")
    body = json.dumps({"to": user.phone, "message": notification.message}).encode(
        "utf-8"
    )
    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": delivery.idempotency_key,
    }
    token = os.getenv("SMS_WEBHOOK_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        endpoint, data=body, headers=headers, method="POST"
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"SMS provider returned HTTP {response.status}")


DELIVERY_PROVIDERS = {"email": _send_email, "sms": _send_sms}


def dispatch_pending(
    db: Session, *, user_id: int | None = None, limit: int = 100
) -> dict:
    """Attempt due outbox rows once. Failures remain durable and retryable."""
    now = _now()
    query = (
        db.query(NotificationDelivery)
        .filter(
            NotificationDelivery.delivery_status == "Pending",
            (NotificationDelivery.next_attempt_at.is_(None))
            | (NotificationDelivery.next_attempt_at <= now),
        )
        .order_by(NotificationDelivery.id.asc())
    )
    if user_id is not None:
        query = query.join(
            Notification, Notification.id == NotificationDelivery.notification_id
        )
        query = query.filter(Notification.user_id == user_id)
    deliveries = query.limit(limit).all()
    sent = failed = 0
    for delivery in deliveries:
        notification = db.get(Notification, delivery.notification_id)
        user = db.get(User, notification.user_id) if notification else None
        try:
            provider = DELIVERY_PROVIDERS.get(delivery.channel)
            if provider is None:
                raise RuntimeError(f"No provider registered for {delivery.channel}")
            if notification is None or user is None:
                raise RuntimeError("Notification recipient or message no longer exists")
            provider(user, notification, delivery)
            delivery.delivery_status = "Sent"
            delivery.last_error = None
            delivery.next_attempt_at = None
            notification.delivery_status = "Sent"
            sent += 1
        except (
            Exception
        ) as exc:  # provider errors are recorded without losing the event
            delivery.delivery_status = "Failed"
            delivery.attempts += 1
            delivery.last_error = str(exc)[:2000]
            delay_minutes = min(2 ** min(delivery.attempts, 6), 60)
            delivery.next_attempt_at = now + timedelta(minutes=delay_minutes)
            if notification is not None:
                notification.delivery_status = "Failed"
            failed += 1
        delivery.updated_at = now
        if delivery.delivery_status == "Sent":
            delivery.attempts += 1
        db.commit()
    return {"attempted": len(deliveries), "sent": sent, "failed": failed}


def retry_failed(db: Session, *, limit: int = 100) -> dict:
    """Make due failed rows eligible again, preserving their idempotency keys."""
    now = _now()
    rows = (
        db.query(NotificationDelivery)
        .filter(
            NotificationDelivery.delivery_status == "Failed",
            NotificationDelivery.attempts < MAX_ATTEMPTS,
            (NotificationDelivery.next_attempt_at.is_(None))
            | (NotificationDelivery.next_attempt_at <= now),
        )
        .order_by(NotificationDelivery.id.asc())
        .limit(limit)
        .all()
    )
    for row in rows:
        row.delivery_status = "Pending"
        row.next_attempt_at = now
        row.updated_at = now
        notification = db.get(Notification, row.notification_id)
        if notification is not None:
            notification.delivery_status = "Pending"
    db.commit()
    return dispatch_pending(db, limit=limit)
