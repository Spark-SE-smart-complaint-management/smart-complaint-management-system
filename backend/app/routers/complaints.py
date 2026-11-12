from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Category, Complaint, Role, User
from app.schemas import ComplaintCreateIn, ComplaintOut
from app.services.audit import log_action
from app.services.notify import dispatch_pending, notify

router = APIRouter(prefix="/complaints", tags=["complaints"])


def generate_reference_id(complaint_id: int) -> str:
    """Create a stable reference from the database-assigned complaint ID."""
    year = datetime.now(UTC).year
    return f"CMP-{year}-{complaint_id:06d}"

