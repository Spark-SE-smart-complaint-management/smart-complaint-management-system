
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Comment, Complaint, User
from app.routers.complaints import can_view_complaint
from app.schemas import CommentCreateIn, CommentOut
from app.services.audit import log_action


router = APIRouter(prefix="/complaints", tags=["comments"])


def get_accessible_complaint(
    complaint_id: int,
    db: Session,
    user: User,
) -> Complaint:
    """Retrieve a complaint after checking access permissions."""

    complaint = db.get(Complaint, complaint_id)

    if complaint is None or complaint.is_archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    if not can_view_complaint(complaint, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return complaint


@router.post(
    "/{complaint_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    complaint_id: int,
    data: CommentCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add a comment to an accessible complaint."""

    complaint = get_accessible_complaint(
        complaint_id,
        db,
        user,
    )

    content = data.content.strip()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Comment cannot be blank",
        )

    comment = Comment(
        complaint_id=complaint.id,
        author_id=user.id,
        content=content,
    )

    try:
        db.add(comment)
        db.flush()

        log_action(
            db,
            action="COMPLAINT_COMMENT_CREATE",
            complaint_id=complaint.id,
            actor_id=user.id,
            to_value=f"Comment ID: {comment.id}",
            trigger_type="Manual",
        )

        db.commit()
        db.refresh(comment)

        return comment

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save comment",
        )


@router.get(
    "/{complaint_id}/comments",
    response_model=list[CommentOut],
)
def list_comments(
    complaint_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List comments belonging to an accessible complaint."""

    complaint = get_accessible_complaint(
        complaint_id,
        db,
        user,
    )

    return (
        db.query(Comment)
        .filter(Comment.complaint_id == complaint.id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .all()
    )
