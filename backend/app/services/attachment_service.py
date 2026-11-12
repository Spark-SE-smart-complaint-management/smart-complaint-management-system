import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import (
    ALLOWED_ATTACHMENT_CONTENT_TYPES,
    ALLOWED_ATTACHMENT_EXTENSIONS,
    MAX_ATTACHMENT_SIZE,
    UPLOAD_DIR,
)


async def save_attachment(upload: UploadFile) -> dict:
    """Validate and save an uploaded complaint attachment."""

    original_filename = Path(upload.filename or "").name

    if not original_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file extension.",
        )

    if upload.content_type not in ALLOWED_ATTACHMENT_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file content type.",
        )

    content = await upload.read(MAX_ATTACHMENT_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty files are not allowed.",
        )

    if len(content) > MAX_ATTACHMENT_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size must not exceed 10 MB.",
        )

    # Check file signatures instead of trusting the supplied MIME type.
    valid_signature = (
        (extension == ".pdf" and content.startswith(b"%PDF-"))
        or (extension in {".jpg", ".jpeg"} and content.startswith(b"\xff\xd8\xff"))
        or (extension == ".png" and content.startswith(b"\x89PNG\r\n\x1a\n"))
    )

    if not valid_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match its extension.",
        )

    upload_directory = Path(UPLOAD_DIR)
    upload_directory.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid.uuid4().hex}{extension}"
    file_path = upload_directory / stored_filename

    try:
        file_path.write_bytes(content)
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to store attachment.",
        )

    return {
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "content_type": upload.content_type,
        "file_size": len(content),
        "storage_path": str(file_path.resolve()),
    }
