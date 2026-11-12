# Smart Complaint Management System

FastAPI backend for the Smart Complaint Management System. The application code is in `backend/`; contributor guidance and requirement evidence are in `docs/`.

## Local setup

Requirements: Python 3.11 and pip.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:ADMIN_PASSWORD = [System.Net.NetworkCredential]::new('', (Read-Host -AsSecureString 'Choose a local administrator password')).Password
python -m app.seed
python -m uvicorn app.main:app --reload
```

For macOS/Linux, activate with `source .venv/bin/activate`; set `ADMIN_PASSWORD` with the shell's environment-variable syntax before running the seed command. The seed command creates `admin@example.com` unless `ADMIN_EMAIL` is set. It never prints the password. Do not reuse a local password in another environment.

The API is available at <http://127.0.0.1:8000> and interactive API documentation at <http://127.0.0.1:8000/docs>.

## Checks

```powershell
cd backend
python -m ruff format --check app tests
python -m ruff check app tests
python -m compileall -q app tests
python -m pytest -q
```

The GitHub Actions workflow runs these checks for pull requests to `main` and pushes to `main` or `feature/**`. See [CI and team workflow](docs/CI_AND_TEAM_WORKFLOW.md), [security notes](docs/SECURITY_AND_PRIVACY.md), and the [requirements traceability matrix](docs/REQUIREMENTS_TRACEABILITY.md).
