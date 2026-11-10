
from fastapi import FastAPI

from app import models  # noqa: F401 (registers tables)
from app.database import Base, engine
from app.routers import (
    auth,
    categories,
    complaints,
    complaint_status,
    triage,
    users,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Complaint Management System")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(triage.router)
app.include_router(complaints.router)
app.include_router(complaint_status.router)


@app.get("/health")
def health():
    return {"status": "ok"}
