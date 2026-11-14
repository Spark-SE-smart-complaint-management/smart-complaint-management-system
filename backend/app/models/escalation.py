from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)

from app.database import Base


class EscalationHierarchy(Base):
    """REQ-26: Configurable escalation levels per category or department."""

    __tablename__ = "escalation_hierarchies"

    __table_args__ = (
        CheckConstraint(
            """
            (category_id IS NOT NULL AND department IS NULL)
            OR
            (category_id IS NULL AND department IS NOT NULL)
            """,
            name="ck_escalation_scope",
        ),
        CheckConstraint(
            "level >= 1",
            name="ck_escalation_level",
        ),
        Index(
            "uq_escalation_category_level",
            "category_id",
            "level",
            unique=True,
            sqlite_where=text("category_id IS NOT NULL"),
        ),
        Index(
            "uq_escalation_department_level",
            "department",
            "level",
            unique=True,
            sqlite_where=text("department IS NOT NULL"),
        ),
        Index("ix_escalation_category", "category_id"),
        Index("ix_escalation_department", "department"),
    )

    id = Column(Integer, primary_key=True)

    category_id = Column(
        Integer,
        ForeignKey("categories.id"),
        nullable=True,
    )

    department = Column(String(50), nullable=True)

    level = Column(Integer, nullable=False)

    assignee_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    role_name = Column(String(50), nullable=False)

    is_active = Column(Boolean, nullable=False, default=True)