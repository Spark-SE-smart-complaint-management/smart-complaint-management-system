
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Category, Complaint, Role, User
from app.schemas import ComplaintCreateIn, ComplaintOut
from app.services.audit import log_action


router = APIRouter(prefix="/complaints", tags=["complaints"])


def generate_reference_id(db: Session) -> str:
    """Generate the next complaint reference ID for the current year."""
    year = datetime.now(timezone.utc).year
    prefix = f"CMP-{year}-"

    last_complaint = (
        db.query(Complaint)
        .filter(Complaint.reference_id.like(f"{prefix}%"))
        .order_by(Complaint.id.desc())
        .first()
    )

    next_number = 1

    if last_complaint:
        try:
            next_number = (
                int(last_complaint.reference_id.split("-")[-1]) + 1
            )
        except ValueError:
            raise HTTPException(
                status_code=500,
                detail="Unable to generate complaint reference",
            )

    return f"{prefix}{next_number:06d}"


@router.post(
    "",
    response_model=ComplaintOut,
    status_code=status.HTTP_201_CREATED,
)
def create_complaint(
    data: ComplaintCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit a complaint (REQ-6 to REQ-11)."""

    # Validate and normalize input
    title = data.title.strip()
    description = data.description.strip()

    if not title:
        raise HTTPException(
            status_code=422,
            detail="Complaint title cannot be blank",
        )

    if not description:
        raise HTTPException(
            status_code=422,
            detail="Complaint description cannot be blank",
        )

    # Validate category if supplied
    if data.category_id is not None:
        category = db.get(Category, data.category_id)

        if category is None or not category.is_active:
            raise HTTPException(
                status_code=422,
                detail="Invalid or inactive category",
            )

    # Reject duplicate complaints from the same citizen
    duplicate = (
        db.query(Complaint)
        .filter(
            Complaint.complainant_id == user.id,
            Complaint.title == title,
            Complaint.description == description,
        )
        .first()
    )

    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="A similar complaint has already been submitted",
        )

    # Create complaint with retry for reference ID conflicts
    for attempt in range(3):
        complaint = Complaint(
            reference_id=generate_reference_id(db),
            complainant_id=user.id,
            title=title,
            description=description,
            category_id=data.category_id,
        )

        try:
            db.add(complaint)
            db.flush()

            # Record complaint creation in audit log
            log_action(
                db,
                action="COMPLAINT_CREATE",
                complaint_id=complaint.id,
                actor_id=user.id,
                to_value=complaint.reference_id,
                trigger_type="Manual",
            )

            db.commit()
            db.refresh(complaint)

            return complaint

        except IntegrityError:
            db.rollback()

            if attempt == 2:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Could not generate a unique complaint reference. "
                        "Please retry."
                    ),
                )

        except Exception:
            db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Unable to save complaint. Please try again.",
            )


def can_view_complaint(
    complaint: Complaint,
    user: User,
) -> bool:
    """Check whether a user can access a complaint."""

    return (
        user.role in (Role.STAFF, Role.ADMIN)
        or complaint.complainant_id == user.id
    )


@router.get(
    "",
    response_model=list[ComplaintOut],
)
def list_complaints(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List complaints visible to the logged-in user."""

    query = db.query(Complaint).filter(
        Complaint.is_archived.is_(False)
    )

    # Citizens can only list their own complaints
    if user.role == Role.COMPLAINANT:
        query = query.filter(
            Complaint.complainant_id == user.id
        )

    return query.order_by(
        Complaint.created_at.desc()
    ).all()


@router.get(
    "/reference/{reference_id}",
    response_model=ComplaintOut,
)
def get_complaint_by_reference(
    reference_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve a complaint using its unique reference ID."""

    complaint = (
        db.query(Complaint)
        .filter(
            Complaint.reference_id == reference_id,
            Complaint.is_archived.is_(False),
        )
        .first()
    )

    if complaint is None:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found",
        )

    if not can_view_complaint(complaint, user):
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    return complaint


@router.get(
    "/{complaint_id}",
    response_model=ComplaintOut,
)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve a complaint using its database ID."""

    complaint = db.get(Complaint, complaint_id)

    if complaint is None or complaint.is_archived:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found",
        )

    if not can_view_complaint(complaint, user):
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    return complaint
