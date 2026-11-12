# Security and privacy controls

This document records controls implemented in the current backend and deployment controls required from the operator. It does not claim infrastructure protections are active in every deployment.

## Implemented controls

| Area | Control and evidence | SRS mapping |
| --- | --- | --- |
| Passwords | Passwords are bcrypt-hashed; registration checks strength and rejects inputs over bcrypt's 72-byte limit. | REQ-1, REQ-2; NFR security/privacy |
| Sessions | Signed JWTs expire after `JWT_EXPIRE_MINUTES`; each request reloads the user and checks active status. Role access is checked server-side. | REQ-3–5; NFR security/privacy |
| Production secret | Startup fails in `APP_ENV=production` unless `SECRET_KEY` is at least 32 characters. The development fallback is generated per process and is unsuitable for production. | NFR security/privacy |
| Input and access checks | Pydantic schemas validate input; routers enforce role, ownership, and complaint access. See authentication, complaint, status, assignment, comment, and attachment tests. | REQ-1–44 as applicable; NFR security/privacy |
| Attachments | PDF/JPEG/PNG extension, media type, signature, size, count, and complaint access are checked. Storage names are generated; download paths are constrained to the upload directory. | REQ-43–44; NFR security/privacy |
| Audit | Sensitive business actions append audit records without storing credentials. | REQ-19, REQ-30; NFR security/privacy |
| Secret handling | `.env` is Git-ignored. Admin seed credentials are supplied through `ADMIN_PASSWORD`; seed output does not reveal it. | NFR security/privacy |

## Deployment controls still required

- Set `APP_ENV=production` and provide a unique random `SECRET_KEY` of at least 32 characters through the deployment secret store. Changing it invalidates current tokens.
- Terminate HTTPS at the application gateway/reverse proxy and configure secure transport between proxy and application when they cross a network boundary.
- SQLite and the local attachment directory do not encrypt data at rest. Production must use encrypted database and file/object storage, encrypted backups, least-privilege access, and retention/deletion rules appropriate to organizational policy.
- Set `DATABASE_URL` and `UPLOAD_DIR` to managed production services with access controls and backups. Keep secrets and complaint data out of source control and CI logs.
- The app does not itself enforce HTTPS redirect or configure trusted-proxy policy. Restrict API docs and seed operations as needed by the deployment.

## Security verification

Run `python -m pytest -q` from `backend/`. Coverage includes authentication and role denial (`tests/test_auth.py`), complaint ownership (`tests/test_complaints.py`), status permissions (`tests/test_complaint_status.py`), assignment permissions (`tests/test_assignments.py`), and attachment validation/access (`tests/test_comments_attachments.py`). CI runs the complete backend suite on pull requests.

The SRS PDF in `docs/` must be reviewed at implementation sign-off to replace descriptive NFR mapping with exact NFR identifiers and deployment-specific thresholds.
