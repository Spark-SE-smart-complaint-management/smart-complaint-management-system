# Issue #11 — Notifications (REQ-39 to REQ-42)

## Implemented backend behavior

- Complaint submission creates a notification for the complainant.
- Assignment creates notifications for the selected staff member or active staff in the selected department.
- Status changes and resolution notify the complainant; reopening notifies the assigned staff member.
- SLA warning and escalation notification helpers use stable idempotency keys and integrate with the SLA workflow.
- Users can list their in-app inbox, mark one/all notifications read, and manage preferred channels (in_app, email, sms).
- External channel deliveries use a durable outbox with attempt counts, error details, next-attempt timestamps, and bounded retries.
- Administrators can inspect delivery attempts at `GET /notifications/deliveries`, retry eligible failures at `POST /notifications/retry-failed`, and search audit metadata at `GET /notifications/history`.

## Admin history API

`GET /notifications/history` is administrator-only and supports optional `event`, `user_id`, `channel`, and `status` filters plus bounded `limit` and `offset` pagination. It returns recipient user ID, event, channel, delivery state, read state, retry count, last error, and timestamps. It deliberately omits message bodies and recipient contact details to reduce exposure of complaint content.

## Verification

Run from `backend/`:

```powershell
python -m pytest tests/test_notifications.py tests/test_sprint2_integration.py -q
python -m ruff check app tests
python -m ruff format --check app tests
```

Tests cover preference validation, user-scoped inbox access, idempotency, retry after provider failure, SLA helper deduplication, admin-only history access, history filters, and complaint submission/assignment/status event integration.

## Integration boundary

This repository currently contains a FastAPI backend and no citizen/staff frontend. The inbox and preference APIs are ready for UI integration, but this backend change does not claim a completed browser notification-preferences screen or admin history page. Email and SMS delivery require valid deployment SMTP/webhook configuration; tests validate queuing, failure recording, and retry behavior rather than live third-party delivery. SLA warning/escalation events depend on the scheduler and escalation workflow in Issue #7.
