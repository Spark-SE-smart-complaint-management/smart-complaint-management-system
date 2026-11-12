# Sprint 2 validation and known gaps

## Checks included

- `backend/tests/test_reports.py`: dashboard counts, filters, resolution/SLA metrics, CSV formula safety, PDF output, and export limits.
- `backend/tests/test_notifications.py`: channel preferences, user-scoped inbox, notification idempotency, provider failure tracking, retry, and admin delivery visibility.
- `backend/tests/test_sprint2_integration.py`: citizen submission through triage, assignment, status changes, notifications, reopening, and reporting.
- `backend/scripts/load_test.py`: configurable concurrent health/dashboard/inbox reads and complaint submissions; reports overall and per-route p95 and maximum latency against the 3-second read and 2-second submission targets.
- CI runs expected-load (50 clients) and peak-load (500 clients) profiles. The current benchmark uses 10 API workers, 40 thread tokens per worker, and a 15-connection SQLite pool per worker.

## Latest CI evidence

- Formatting, lint, compile checks, and all 90 backend tests passed.
- Expected load (50 concurrent clients, 150 reads): p95 0.342 s, maximum 0.534 s; five submissions max 0.076 s; no failures. The SRS target check passed.
- Peak load (500 concurrent clients, 1,500 reads): latest run p95 5.251 s and maximum 6.063 s; five submissions max 0.060 s; no failures. A previous run with the same settings measured p95 3.227 s and maximum 3.871 s. Both exceed the 3-second read target, and the results vary with hosted runner capacity.
- Concurrent complaint reference generation now uses the database-assigned complaint ID; the latest submission runs completed without reference conflicts.
- These are GitHub-hosted CI measurements, not production-hardware results.

Run the full backend suite with `python -m pytest backend/tests -q`; run lint with `python -m ruff check backend`. The expected and peak load commands are in `.github/workflows/backend-tests.yml`.

## Acceptance gaps and dependencies

- Issue #7 (owned by `sanjayv-044`) remains open. Scheduled SLA escalation, 50,000-open-complaint scheduler timing, recipient routing, and scheduler-to-notification integration depend on that work.
- Issue #8 (owned by `sanjayv-044`) remains open. SLA-specific monitoring/reporting requires its reporting definitions and data.
- The repository contains no browser UI. Keyboard navigation, focus order, contrast, screen-reader announcements, and other browser accessibility checks need the team's UI.
- Email and SMS adapters require deployment credentials/provider endpoints. Automated coverage verifies queuing, failure recording, and retry behavior; it does not claim live provider delivery.
- End-to-end tests use the API test client and synthetic data. The team still needs a live multi-service demo and deployment recovery exercise before release.
