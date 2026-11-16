from datetime import UTC, datetime, timedelta

from app.models import Notification, NotificationDelivery, Role
from app.services import notify as notify_service
from app.services.notify import (
    dispatch_pending,
    notify,
    notify_escalation,
    notify_sla_at_risk,
    retry_failed,
)

from tests.conftest import auth_header, make_user


def test_preferences_delivery_log_retry_and_idempotency(client, db, monkeypatch):
    user = make_user(db, "notification-user@example.com")
    headers = auth_header(client, user.email)
    assert client.get("/notifications/preferences", headers=headers).json() == {
        "channels": ["in_app"]
    }
    assert (
        client.put(
            "/notifications/preferences",
            json={"channels": ["in_app", "email"]},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/notifications/preferences",
            json={"channels": ["email", "email"]},
            headers=headers,
        ).status_code
        == 422
    )

    attempts = []

    def transient_failure(_user, _notification, _delivery):
        attempts.append("failed")
        raise RuntimeError("temporary mail outage")

    monkeypatch.setitem(notify_service.DELIVERY_PROVIDERS, "email", transient_failure)
    notify(
        db,
        user.id,
        "COMPLAINT_STATUS_CHANGED",
        "Complaint CMP-2026-700001 status changed to In Progress.",
        idempotency_key="complaint:1:status:1",
    )
    db.commit()
    result = dispatch_pending(db, user_id=user.id)
    assert result == {"attempted": 1, "sent": 0, "failed": 1}
    email_delivery = (
        db.query(NotificationDelivery)
        .filter_by(channel="email", delivery_status="Failed")
        .one()
    )
    assert "temporary mail outage" in email_delivery.last_error
    email_delivery.next_attempt_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(
        seconds=1
    )
    db.commit()

    monkeypatch.setitem(
        notify_service.DELIVERY_PROVIDERS,
        "email",
        lambda _user, _notification, _delivery: attempts.append("sent"),
    )
    retried = retry_failed(db, limit=10)
    assert retried == {"attempted": 1, "sent": 1, "failed": 0}
    assert attempts == ["failed", "sent"]
    assert email_delivery.delivery_status == "Sent"
    assert email_delivery.attempts == 2

    before = db.query(Notification).filter_by(user_id=user.id).count()
    notify(
        db,
        user.id,
        "COMPLAINT_STATUS_CHANGED",
        "Complaint CMP-2026-700001 status changed to In Progress.",
        idempotency_key="complaint:1:status:1",
    )
    db.commit()
    assert db.query(Notification).filter_by(user_id=user.id).count() == before
    inbox = client.get("/notifications", headers=headers)
    assert inbox.status_code == 200
    notification_id = inbox.json()[0]["id"]
    assert (
        client.patch(
            f"/notifications/{notification_id}/read", headers=headers
        ).status_code
        == 200
    )
    other = make_user(db, "notification-other@example.com")
    assert (
        client.patch(
            f"/notifications/{notification_id}/read",
            headers=auth_header(client, other.email),
        ).status_code
        == 404
    )
    admin = make_user(db, "notification-admin@example.com", Role.ADMIN)
    assert (
        client.get(
            "/notifications/deliveries", headers=auth_header(client, admin.email)
        ).status_code
        == 200
    )


def test_sla_event_helpers_deduplicate_per_recipient(db):
    staff = make_user(db, "notification-sla-staff@example.com", Role.STAFF)
    admin = make_user(db, "notification-sla-admin@example.com", Role.ADMIN)
    warning = notify_sla_at_risk(
        db,
        complaint_id=17,
        reference_id="CMP-2026-700017",
        recipient_id=staff.id,
        event_id="warning-1",
    )
    duplicate_warning = notify_sla_at_risk(
        db,
        complaint_id=17,
        reference_id="CMP-2026-700017",
        recipient_id=staff.id,
        event_id="warning-1",
    )
    assert warning[0].id == duplicate_warning[0].id

    first = notify_escalation(
        db,
        complaint_id=17,
        reference_id="CMP-2026-700017",
        recipient_ids=[staff.id, admin.id, staff.id],
        event_id="escalation-1",
    )
    assert len(first) == 2
    assert {row.user_id for row in first} == {staff.id, admin.id}
    assert db.query(NotificationDelivery).count() == 3


def test_admin_notification_history_filters_and_hides_message_content(client, db):
    recipient = make_user(db, "notification-history-user@example.com")
    admin = make_user(db, "notification-history-admin@example.com", Role.ADMIN)
    notify(
        db, recipient.id, "COMPLAINT_SUBMITTED",
        "Private complaint description must not appear in admin history.",
        channel="in_app", idempotency_key="history:submitted:1",
    )
    notify(
        db, recipient.id, "COMPLAINT_STATUS_CHANGED",
        "Complaint CMP-2026-700002 status changed.",
        channel="email", idempotency_key="history:status:2",
    )
    db.commit()

    user_headers = auth_header(client, recipient.email)
    assert client.get("/notifications/history", headers=user_headers).status_code == 403

    admin_headers = auth_header(client, admin.email)
    response = client.get(
        "/notifications/history?event=COMPLAINT_SUBMITTED&channel=in_app",
        headers=admin_headers,
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["user_id"] == recipient.id
    assert rows[0]["event"] == "COMPLAINT_SUBMITTED"
    assert rows[0]["channel"] == "in_app"
    assert rows[0]["delivery_status"] == "Sent"
    assert "message" not in rows[0]
    assert "Private complaint description" not in response.text

    failed = client.get("/notifications/history?status=Failed", headers=admin_headers)
    assert failed.status_code == 200
    assert failed.json() == []
