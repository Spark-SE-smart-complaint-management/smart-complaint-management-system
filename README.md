# smart-complaint-management-system

Backend (FastAPI) in `backend/`.

## Run locally
```
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows  (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m app.seed            # creates admin@example.com / Admin@12345
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

## Test
```
cd backend
python -m pytest -q
```
