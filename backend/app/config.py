
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./scms.db")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = "HS256"

# REQ-3: token validity is configurable
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# REQ-21: Complaint reopening grace period (default: 7 days)
REOPEN_GRACE_PERIOD_DAYS = int(
    os.getenv("REOPEN_GRACE_PERIOD_DAYS", "7")
)

# REQ-43/44: Complaint attachment configuration
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "backend/uploads/complaints")
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ATTACHMENTS_PER_COMPLAINT = 5

ALLOWED_ATTACHMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

ALLOWED_ATTACHMENT_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}
