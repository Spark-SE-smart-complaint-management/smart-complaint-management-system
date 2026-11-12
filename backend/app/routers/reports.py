"""Administrator dashboard and safe CSV/PDF exports (REQ-35 to REQ-38)."""

import csv
import io
from datetime import date, datetime, time, timedelta
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.database import get_db
from app.deps import require_role
from app.models import AuditLog, Category, Complaint, Role, SLAStatus, Status, User

router = APIRouter(prefix="/reports", tags=["reports"])
admin_only = require_role(Role.ADMIN)
CSV_EXPORT_LIMIT = 10_000
PDF_EXPORT_LIMIT = 1_000


def _filtered_query(
    db: Session,
    *,
    start_date: date | None,
    end_date: date | None,
    category_id: int | None,
    department: str | None,
):
    assignee = aliased(User)
    query = (
        db.query(Complaint)
        .outerjoin(Category, Complaint.category_id == Category.id)
        .outerjoin(assignee, Complaint.assignee_id == assignee.id)
        .filter(Complaint.is_archived.is_(False))
    )
    if start_date is not None:
        start = datetime.combine(start_date, time.min)
        query = query.filter(Complaint.created_at >= start)
    if end_date is not None:
        end_exclusive = datetime.combine(end_date + timedelta(days=1), time.min)
        query = query.filter(Complaint.created_at < end_exclusive)
    if category_id is not None:
        query = query.filter(Complaint.category_id == category_id)
    if department is not None:
        effective_department = func.lower(
            func.coalesce(
                Complaint.assigned_department,
                assignee.department,
                Category.department,
            )
        )
        query = query.filter(effective_department == department.strip().lower())
    return query, assignee


def _filters(
    db: Session,
    start_date: date | None,
    end_date: date | None,
    category_id: int | None,
    department: str | None,
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(422, "start_date must be on or before end_date")
    return _filtered_query(
        db,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        department=department,
    )


def _dashboard_data(
    db: Session,
    start_date: date | None,
    end_date: date | None,
    category_id: int | None,
    department: str | None,
):
    query, _ = _filters(db, start_date, end_date, category_id, department)
    total = query.with_entities(func.count(Complaint.id)).scalar() or 0
    raw_status_counts = dict(
        query.with_entities(Complaint.status, func.count(Complaint.id))
        .group_by(Complaint.status)
        .all()
    )
    status_counts = {
        status.value: int(raw_status_counts.get(status, 0)) for status in Status
    }

    tracked = (
        query.filter(Complaint.sla_deadline.is_not(None))
        .with_entities(func.count(Complaint.id))
        .scalar()
        or 0
    )
    breached = (
        query.filter(Complaint.sla_deadline.is_not(None))
        .filter(Complaint.sla_status == SLAStatus.BREACHED)
        .with_entities(func.count(Complaint.id))
        .scalar()
        or 0
    )

    resolved_at = (
        db.query(
            AuditLog.complaint_id.label("complaint_id"),
            func.min(AuditLog.timestamp).label("resolved_at"),
        )
        .filter(
            AuditLog.action == "STATUS_CHANGE",
            AuditLog.to_value == Status.RESOLVED.value,
            AuditLog.complaint_id.is_not(None),
        )
        .group_by(AuditLog.complaint_id)
        .subquery()
    )
    if db.bind.dialect.name == "sqlite":
        duration_hours = (
            func.julianday(resolved_at.c.resolved_at)
            - func.julianday(Complaint.created_at)
        ) * 24
    else:
        duration_hours = (
            func.extract("epoch", resolved_at.c.resolved_at - Complaint.created_at)
            / 3600
        )
    average_hours = (
        query.join(resolved_at, resolved_at.c.complaint_id == Complaint.id)
        .with_entities(func.avg(duration_hours))
        .scalar()
    )

    category_rows = (
        query.with_entities(
            func.coalesce(Category.name, "Uncategorized"), func.count(Complaint.id)
        )
        .group_by(Category.name)
        .order_by(Category.name)
        .all()
    )
    priority_rows = (
        query.with_entities(Complaint.priority, func.count(Complaint.id))
        .group_by(Complaint.priority)
        .all()
    )
    return {
        "filters": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "category_id": category_id,
            "department": department,
        },
        "metrics": {
            "total_complaints": int(total),
            "status_counts": status_counts,
            "average_resolution_hours": (
                round(float(average_hours), 2) if average_hours is not None else None
            ),
            "sla_tracked_complaints": int(tracked),
            "sla_breached_complaints": int(breached),
            "sla_breach_rate_percent": (
                round(100 * breached / tracked, 2) if tracked else 0.0
            ),
        },
        "category_distribution": [
            {"category": name, "count": int(count)} for name, count in category_rows
        ],
        "priority_distribution": [
            {
                "priority": priority.value if priority else "Unassigned",
                "count": int(count),
            }
            for priority, count in priority_rows
        ],
    }


def _complaint_rows(
    db: Session,
    start_date: date | None,
    end_date: date | None,
    category_id: int | None,
    department: str | None,
    limit: int,
):
    query, assignee = _filters(db, start_date, end_date, category_id, department)
    rows = (
        query.with_entities(
            Complaint, Category.name, Category.department, assignee.department
        )
        .order_by(Complaint.created_at.desc(), Complaint.id.desc())
        .limit(limit + 1)
        .all()
    )
    if len(rows) > limit:
        raise HTTPException(
            413,
            f"Export exceeds the {limit:,}-row limit. Narrow the date or department filters.",
        )
    return rows


def _safe_csv_cell(value) -> str:
    text = "" if value is None else str(value)
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


@router.get("/dashboard")
def get_dashboard(
    start_date: date | None = None,
    end_date: date | None = None,
    category_id: int | None = Query(default=None, ge=1),
    department: str | None = Query(default=None, min_length=1, max_length=50),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    return _dashboard_data(db, start_date, end_date, category_id, department)


@router.get("/export")
def export_dashboard(
    format: str = Query(default="csv", pattern="^(csv|pdf)$"),
    start_date: date | None = None,
    end_date: date | None = None,
    category_id: int | None = Query(default=None, ge=1),
    department: str | None = Query(default=None, min_length=1, max_length=50),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    dashboard = _dashboard_data(db, start_date, end_date, category_id, department)
    limit = PDF_EXPORT_LIMIT if format == "pdf" else CSV_EXPORT_LIMIT
    rows = _complaint_rows(db, start_date, end_date, category_id, department, limit)
    if format == "csv":
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        metrics = dashboard["metrics"]
        writer.writerow(["Smart Complaint Management report"])
        writer.writerow(["Total complaints", metrics["total_complaints"]])
        writer.writerow(
            ["Average resolution hours", metrics["average_resolution_hours"]]
        )
        writer.writerow(["SLA breach rate percent", metrics["sla_breach_rate_percent"]])
        writer.writerow([])
        writer.writerow(
            [
                "Reference",
                "Created at (UTC)",
                "Title",
                "Status",
                "Category",
                "Priority",
                "Department",
            ]
        )
        for complaint, category_name, category_department, assignee_department in rows:
            effective_department = (
                complaint.assigned_department
                or assignee_department
                or category_department
            )
            writer.writerow(
                [
                    _safe_csv_cell(complaint.reference_id),
                    _safe_csv_cell(complaint.created_at),
                    _safe_csv_cell(complaint.title),
                    _safe_csv_cell(complaint.status.value),
                    _safe_csv_cell(category_name),
                    _safe_csv_cell(
                        complaint.priority.value if complaint.priority else None
                    ),
                    _safe_csv_cell(effective_department),
                ]
            )
        return Response(
            content=stream.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="complaint-report.csv"'
            },
        )

    from reportlab.lib.enums import TA_LEFT

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.4 * inch,
        leftMargin=0.4 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
        title="Smart Complaint Management report",
    )
    styles = getSampleStyleSheet()
    styles["BodyText"].alignment = TA_LEFT
    story = [
        Paragraph("Smart Complaint Management report", styles["Title"]),
        Spacer(1, 8),
    ]
    story.append(
        Paragraph(
            escape(
                "Filters: "
                + ", ".join(
                    f"{key}={value}"
                    for key, value in dashboard["filters"].items()
                    if value is not None
                )
                or "none"
            ),
            styles["BodyText"],
        )
    )
    metrics = dashboard["metrics"]
    summary = [
        ["Metric", "Value"],
        ["Total complaints", str(metrics["total_complaints"])],
        ["Average resolution (hours)", str(metrics["average_resolution_hours"])],
        ["SLA breach rate (%)", str(metrics["sla_breach_rate_percent"])],
    ]
    story.extend([Spacer(1, 8), Table(summary, repeatRows=1), Spacer(1, 12)])
    table_data = [
        [
            "Reference",
            "Created (UTC)",
            "Title",
            "Status",
            "Category",
            "Priority",
            "Department",
        ]
    ]
    for complaint, category_name, category_department, assignee_department in rows:
        effective_department = (
            complaint.assigned_department
            or assignee_department
            or category_department
            or "Unassigned"
        )
        table_data.append(
            [
                Paragraph(escape(complaint.reference_id), styles["BodyText"]),
                Paragraph(escape(str(complaint.created_at)), styles["BodyText"]),
                Paragraph(escape(complaint.title), styles["BodyText"]),
                Paragraph(escape(complaint.status.value), styles["BodyText"]),
                Paragraph(escape(category_name or "Uncategorized"), styles["BodyText"]),
                Paragraph(
                    escape(
                        complaint.priority.value if complaint.priority else "Unassigned"
                    ),
                    styles["BodyText"],
                ),
                Paragraph(escape(effective_department), styles["BodyText"]),
            ]
        )
    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            1.05 * inch,
            1.35 * inch,
            2.6 * inch,
            1.05 * inch,
            1.35 * inch,
            0.9 * inch,
            1.25 * inch,
        ],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B7C9D6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F2F6FA")],
                ),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="complaint-report.pdf"'},
    )
