from fastapi import FastAPI

from app import models  # noqa: F401 (registers tables)
from app.config import validate_security_config
from app.database import Base, engine
from app.routers import (
    assignments,
    attachments,
    auth,
    categories,
    comments,
    complaint_status,
    complaints,
    notifications,
    reports,
    triage,
    users,
)

validate_security_config()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Complaint Management System")

# Authentication and user management
app.include_router(auth.router)
app.include_router(users.router)

# Complaint management
app.include_router(categories.router)
app.include_router(triage.router)
app.include_router(complaints.router)
app.include_router(complaint_status.router)
app.include_router(assignments.router)

# Issue #10: Comments and attachments
app.include_router(comments.router)
app.include_router(attachments.router)
app.include_router(notifications.router)
app.include_router(reports.router)


@app.get("/health")
def health():
    return {"status": "ok"}
