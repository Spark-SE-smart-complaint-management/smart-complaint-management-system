# Sprint 2 validation and known gaps

## Checks included

- `backend/tests/test_reports.py`: dashboard counts, filters, resolution/SLA metrics, CSV formula safety, PDF output, and export limits.
- `backend/tests/test_notifications.py`: channel preferences, user-scoped inbox, notification idempotency, provider failure tracking, retry, and admin delivery visibility.
- `backend/tests/test_sprint2_integration.py`: citizen submission through triage, assignment, status changes, notifications, reopening, and reporting.
- `backend/scripts/load_test.py`: sends one authenticated read request per simulated client, distributed across health, dashboard, and notifications. It reports overall and per-route p95 and maximum latency against the 3-second read and 2-second submission targets.
- CI runs expected (50 concurrent clients) and peak (500 concurrent clients) profiles. The benchmark uses 10 API workers, 40 thread tokens per worker, and a 40-connection SQLite pool per worker.

## Latest CI evidence

- Formatting, lint, compile checks, and all 90 backend tests passed.
- Expected profile (50 concurrent read requests): p95 0.094 s, maximum 0.096 s; five submissions max 0.073 s; no failures.
- Peak profile (500 concurrent read requests): p95 0.877 s, maximum 0.936 s; five submissions max 0.029 s; no failures. Both profiles passed the SRS response-time targets.
- Concurrent complaint reference generation now uses the database-assigned complaint ID; the submission samples completed without reference conflicts.
- Notification provider failure and retry behavior is covered by tests. These are GitHub-hosted CI measurements, not production-hardware results.

Run the full backend suite with `python -m pytest backend/tests -q`; run lint with `python -m ruff check backend`. The expected and peak load commands are in `.github/workflows/backend-tests.yml`.

## Acceptance gaps and dependencies

- The repository contains no citizen/staff application UI. Keyboard navigation, focus order, contrast, and screen-reader interaction cannot be checked here and must be verified against the team's UI.
- Issue #7 (owned by `sanjayv-044`) remains open. Scheduled SLA escalation, 50,000-open-complaint scheduler timing, recipient routing, and scheduler-to-notification integration depend on that work.
- Issue #8 (owned by `sanjayv-044`) remains open. SLA-specific monitoring/reporting requires its reporting definitions and data.
- Email and SMS adapters require deployment credentials/provider endpoints. Automated coverage verifies queuing, failure recording, and retry behavior; it does not claim live provider delivery.
- End-to-end tests use the API test client and synthetic data. The team still needs a live multi-service demo and deployment recovery exercise before release.
