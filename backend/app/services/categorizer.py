"""REQ-13: keyword-based category suggestion. Suggests only; staff confirm via the category endpoint."""

import re

from sqlalchemy.orm import Session

from app.models import Category

# Keys are lower-case category names. Categories not listed here still match on their own name.
KEYWORDS: dict[str, list[str]] = {
    "billing": [
        "bill",
        "invoice",
        "charge",
        "refund",
        "payment",
        "overcharg",
        "price",
        "fee",
        "subscription",
    ],
    "technical": [
        "internet",
        "network",
        "error",
        "bug",
        "crash",
        "login",
        "outage",
        "down",
        "slow",
        "server",
        "wifi",
        "connection",
        "not working",
        "app",
    ],
    "service quality": [
        "service",
        "delay",
        "quality",
        "poor",
        "waiting",
        "late",
        "unresolved",
        "broken",
    ],
    "staff behaviour": [
        "rude",
        "behaviour",
        "behavior",
        "staff",
        "abusive",
        "attitude",
        "impolite",
        "harass",
        "unprofessional",
        "misbehav",
    ],
}


def suggest_category(db: Session, text: str) -> Category | None:
    text_l = text.lower()
    best, best_score = None, 0
    for cat in (
        db.query(Category).filter(Category.is_active.is_(True)).order_by(Category.id)
    ):
        words = KEYWORDS.get(cat.name.lower(), []) + [cat.name.lower()]
        score = sum(1 for w in words if re.search(r"\b" + re.escape(w), text_l))
        if score > best_score:
            best, best_score = cat, score
    return best
