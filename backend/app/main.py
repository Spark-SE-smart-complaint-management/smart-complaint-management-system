from fastapi import FastAPI

from app import models  # noqa: F401  (registers tables)
from app.database import Base, engine
from app.routers import auth, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Complaint Management System")
app.include_router(auth.router)
app.include_router(users.router)
# Later phases: complaints, categories, assignment, escalation, sla, dashboard


@app.get("/health")
def health():
    return {"status": "ok"}
