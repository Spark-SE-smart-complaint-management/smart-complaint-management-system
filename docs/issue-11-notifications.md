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

## Scheduled outbox worker

External delivery rows are dispatched by a separate scheduler process. Start it from the repository's `backend/` directory with:

```powershell
python -m app.scheduler
```

The scheduler runs the existing SLA cycle every 15 minutes and the notification outbox cycle every minute. Each notification cycle processes at most `NOTIFICATION_BATCH_SIZE` due rows (default 100), records provider failures, and retries only rows whose exponential-backoff deadline has elapsed. The process uses a fresh database session per cycle and closes it after success or failure. Run one scheduler instance per deployment; the APScheduler job also prevents overlapping executions within that process.

## Provider configuration

Set provider settings in the deployment secret manager/environment, never commit real credentials:

| Variable | Purpose |
| --- | --- |
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP port (default 587) |
| `SMTP_SENDER` | Verified sender address |
| `SMTP_USER`, `SMTP_PASSWORD` | Optional SMTP authentication |
| `SMTP_USE_SSL` | Set `true` for implicit TLS; otherwise STARTTLS is used |
| `SMTP_TIMEOUT_SECONDS` | SMTP connection timeout (default 10 seconds) |
| `SMS_WEBHOOK_URL` | HTTPS endpoint for the organization's SMS gateway |
| `SMS_WEBHOOK_TOKEN` | Optional bearer token for the SMS gateway |
| `NOTIFICATION_BATCH_SIZE` | Maximum due outbox rows processed each minute (default 100) |

An absent provider configuration is treated as a delivery failure, not a successful send. Configure and verify a real SMTP account and an authenticated SMS gateway before claiming live email/SMS acceptance. The SMS gateway must accept the `to` and `message` JSON fields and honor the `Idempotency-Key` header to protect against duplicate sends after network timeouts.

## Remaining integration acceptance

- The citizen/staff inbox and preference screens and the administrator history screen must be connected in the frontend repository.
- Deployment must run exactly one `python -m app.scheduler` process alongside the API service, with health monitoring and restart policy.
- A deployment operator must configure provider secrets and run end-to-end delivery tests using approved test recipients.
- Browser accessibility checks apply to the frontend and cannot be completed in this backend-only repository.
