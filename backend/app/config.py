import os
import secrets

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./scms.db")
APP_ENV = os.getenv("APP_ENV", "development").lower()
# This fallback is only for local development. Production startup validates that
# an operator supplied a high-entropy key through the environment.
SECRET_KEY = os.getenv("SECRET_KEY") or (
    secrets.token_urlsafe(48) if APP_ENV == "development" else ""
)
JWT_ALGORITHM = "HS256"


def validate_security_config() -> None:
    """Fail closed when production is started with unsafe auth settings."""
    if APP_ENV == "production" and len(SECRET_KEY) < 32:
        raise RuntimeError("Production requires SECRET_KEY with at least 32 characters")


# REQ-3: token validity is configurable
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# REQ-21: Complaint reopening grace period (default: 7 days)
REOPEN_GRACE_PERIOD_DAYS = int(os.getenv("REOPEN_GRACE_PERIOD_DAYS", "7"))

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
