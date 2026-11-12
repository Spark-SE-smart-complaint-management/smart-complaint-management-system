# Sprint 2 demo runbook

This backend-only demo exercises complaint submission, automatic triage and assignment, staff status updates, notifications, dashboard metrics, and CSV/PDF exports using synthetic data.

## Prepare the demo

1. Follow the Python setup steps in the root README and apply `backend/migrations/007_notification_delivery.sql` after migrations 001–006.
2. Set `DATABASE_URL` to a disposable local database, `ADMIN_PASSWORD` to a strong local-only password, and `DEMO_PASSWORD` to a strong password used only by the seed accounts. Do not reuse production credentials.
3. Start the API from `backend` with `uvicorn app.main:app --reload`.
4. In another terminal, run `python scripts/demo_seed.py`. The fixed demo references make repeated runs safe; they do not recreate or overwrite existing demo records.

## Walk through the demo

1. Sign in through `POST /auth/login` using the seeded admin, citizen, and staff accounts (`admin@demo.local`, `citizen@demo.local`, `staff@demo.local`) and the local `DEMO_PASSWORD`.
2. As the citizen, submit a complaint at `POST /complaints`. The API runs triage and assignment and adds a submission notification.
3. As staff, update the assigned complaint through `PATCH /complaints/{id}/status` to `In Progress`, then `Resolved`. As admin, close it or exercise the reopen flow.
4. As each account, view and mark in-app notifications using `GET /notifications`, `PATCH /notifications/{id}/read`, and `POST /notifications/read-all`. Set channel preferences with `PUT /notifications/preferences`.
5. As admin, view `GET /reports/dashboard`, then download `GET /reports/export?format=csv` or `?format=pdf`. Date, category, and department filters are available on both report endpoints.

External delivery stays disabled unless SMTP or the SMS webhook is configured. Provider outages are recorded for retry; demo runs do not send to real recipients.

For a repeatable read-only load sample after seeding, run `python scripts/load_test.py --base-url http://127.0.0.1:8000 --token <admin-token>`. Use `--submit-count N` only when you want to add N synthetic complaints.
