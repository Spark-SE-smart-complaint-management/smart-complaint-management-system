from sqlalchemy.orm import Session

from app.models import Notification


def notify(
    db: Session, user_id: int, event: str, message: str, channel: str = "in_app"
) -> Notification:
    """Stub for now: stores an in-app notification row (REQ-42).
    Issue #11 can later plug in email/SMS behind this same function. Caller commits."""
    n = Notification(user_id=user_id, event=event, message=message, channel=channel)
    db.add(n)
    return n
