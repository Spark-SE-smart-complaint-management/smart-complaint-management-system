# Sprint 2 validation and known gaps

## Checks included

- `backend/tests/test_reports.py`: dashboard counts, filters, resolution/SLA metrics, CSV formula safety, PDF output, and export limits.
- `backend/tests/test_notifications.py`: channel preferences, user-scoped inbox, notification idempotency, provider failure tracking, retry, and admin delivery visibility.
- `backend/tests/test_sprint2_integration.py`: citizen submission through triage, assignment, status changes, notifications, reopening, and reporting.
- `backend/scripts/load_test.py`: configurable concurrent health/dashboard/inbox reads and complaint submissions; reports overall and per-route maximum and p95 latency against the issue's 3-second read and 2-second submission targets. CI runs 500 concurrent synthetic read journeys and five concurrent complaint submissions against an eight-worker local API process. The best observed run completed 1,500 reads with p95 3.336 s and maximum 3.928 s; it recorded no failures but missed the 3-second read target. Subsequent hosted runs varied (p95 3.880–6.321 s; maximum 4.453–7.244 s), also with no read request failures. Five submissions stayed under 0.1 s maximum. These are GitHub-hosted CI measurements, not production hardware results.

Run the full backend suite with `python -m pytest backend/tests -q`; run lint with `python -m ruff check backend`. Record the environment, concurrency, complaint count, and output when running the load sample. GitHub Actions provides a repeatable Linux-hosted 500-concurrent-user smoke sample; it is a CI reference measurement and does not replace production-like deployment testing.

## Acceptance gaps and dependencies

- Issue #7 (owned by `sanjayv-044`) is still open. Scheduled SLA at-risk/escalation detection, 50,000-open-complaint scheduler timing, recipient routing for escalation, and scheduler-to-notification integration need that work.
- Issue #8 (owned by `sanjayv-044`) is still open. SLA-specific monitoring/reporting cannot be fully accepted until its reporting definitions and data are integrated with the dashboard.
- The repository is backend-only. Keyboard navigation, focus order, contrast, screen-reader announcements, and other browser accessibility checks need the team's UI.
- Email and SMS adapters require deployment credentials/provider endpoints. Local automated coverage verifies queuing, failure recording, and retry behavior; it does not claim delivery through a live provider.
- The end-to-end test uses the API test client and synthetic users/data. A live multi-service demo and deployment recovery exercise should be recorded by the team before release.
