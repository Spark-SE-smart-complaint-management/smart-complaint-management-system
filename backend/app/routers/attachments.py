
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import MAX_ATTACHMENTS_PER_COMPLAINT, UPLOAD_DIR
from app.database import get_db
from app.deps import get_current_user
from app.models import Attachment, Complaint, User
from app.routers.complaints import can_view_complaint
from app.services.attachment_service import save_attachment
from app.services.audit import log_action


router = APIRouter(prefix="/complaints", tags=["attachments"])


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
    "/{complaint_id}/attachments",
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachments(
    complaint_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload attachments to a complaint."""

    complaint = get_accessible_complaint(
        complaint_id,
        db,
        user,
    )

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file is required",
        )

    existing_count = (
        db.query(Attachment)
        .filter(Attachment.complaint_id == complaint.id)
        .count()
    )

    if existing_count + len(files) > MAX_ATTACHMENTS_PER_COMPLAINT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A complaint can have at most 5 attachments",
        )

    saved_paths = []

    try:
        uploaded_attachments = []

        for upload in files:
            metadata = await save_attachment(upload)
            saved_paths.append(Path(metadata["storage_path"]))

            attachment = Attachment(
                complaint_id=complaint.id,
                uploaded_by=user.id,
                **metadata,
            )

            db.add(attachment)
            db.flush()

            log_action(
                db,
                action="COMPLAINT_ATTACHMENT_UPLOAD",
                complaint_id=complaint.id,
                actor_id=user.id,
                to_value=f"Attachment ID: {attachment.id}",
                trigger_type="Manual",
            )

            uploaded_attachments.append({
                "id": attachment.id,
                "original_filename": attachment.original_filename,
                "content_type": attachment.content_type,
                "file_size": attachment.file_size,
            })

        db.commit()

        return {
            "message": "Attachments uploaded successfully",
            "attachments": uploaded_attachments,
        }

    except HTTPException:
        db.rollback()

        for path in saved_paths:
            path.unlink(missing_ok=True)

        raise

    except Exception:
        db.rollback()

        for path in saved_paths:
            path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to upload attachments",
        )

    finally:
        for upload in files:
            await upload.close()


@router.get(
    "/{complaint_id}/attachments/{attachment_id}",
)
def download_attachment(
    complaint_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Download an attachment after checking complaint access."""

    complaint = get_accessible_complaint(
        complaint_id,
        db,
        user,
    )

    attachment = (
        db.query(Attachment)
        .filter(
            Attachment.id == attachment_id,
            Attachment.complaint_id == complaint.id,
        )
        .first()
    )

    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    upload_directory = Path(UPLOAD_DIR).resolve()
    file_path = Path(attachment.storage_path).resolve()

    if not file_path.is_relative_to(upload_directory):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid attachment storage path",
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment file not found",
        )

    log_action(
        db,
        action="COMPLAINT_ATTACHMENT_DOWNLOAD",
        complaint_id=complaint.id,
        actor_id=user.id,
        to_value=f"Attachment ID: {attachment.id}",
        trigger_type="Manual",
    )

    db.commit()

    return FileResponse(
        path=file_path,
        media_type=attachment.content_type,
        filename=attachment.original_filename,
    )
