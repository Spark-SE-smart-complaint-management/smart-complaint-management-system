"""SLA compliance reporting for REQ-34."""

import csv
import io
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.database import get_db
from app.deps import require_role
from app.models import AuditLog, Category, Complaint, Role, Status, User

router = APIRouter(prefix="/reports", tags=["SLA compliance"])
admin_only = require_role(Role.ADMIN)


def _naive_utc(value: datetime) -> datetime:
    return (
        value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
    )


def _sla_rows(db, start_date, end_date, category_id, department):
    assignee = aliased(User)
    query = (
        db.query(Complaint, Category.name, Category.department, assignee.department)
        .outerjoin(Category, Complaint.category_id == Category.id)
        .outerjoin(assignee, Complaint.assignee_id == assignee.id)
        .filter(Complaint.is_archived.is_(False), Complaint.sla_deadline.is_not(None))
    )
    if start_date:
        query = query.filter(
            Complaint.created_at >= datetime.combine(start_date, time.min)
        )
    if end_date:
        query = query.filter(
            Complaint.created_at
            < datetime.combine(end_date + timedelta(days=1), time.min)
        )
    if category_id is not None:
        query = query.filter(Complaint.category_id == category_id)
    if department:
        effective_department = func.lower(
            func.coalesce(
                Complaint.assigned_department, assignee.department, Category.department
            )
        )
        query = query.filter(effective_department == department.strip().lower())
    return query.order_by(Complaint.created_at.asc(), Complaint.id.asc()).all()


def _first_resolution_time(db, complaint_id):
    event = (
        db.query(AuditLog.timestamp)
        .filter(
            AuditLog.complaint_id == complaint_id,
            AuditLog.action == "STATUS_CHANGE",
            AuditLog.to_value == Status.RESOLVED.value,
        )
        .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
        .first()
    )
    return event[0] if event else None


def build_sla_compliance_report(
    db, start_date=None, end_date=None, category_id=None, department=None
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(422, "start_date must be on or before end_date")

    groups = {}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for complaint, category_name, category_department, assignee_department in _sla_rows(
        db, start_date, end_date, category_id, department
    ):
        effective_department = (
            complaint.assigned_department
            or assignee_department
            or category_department
            or "Unassigned"
        )
        category = category_name or "Uncategorized"
        priority = complaint.priority.value if complaint.priority else "Unassigned"
        key = (category, effective_department, priority)
        row = groups.setdefault(
            key,
            {
                "category": category,
                "total_complaints": 0,
                "priority": priority,
                "resolved_within_sla": 0,
                "sla_breached_count": 0,
                "department": effective_department,
                "_resolved_count": 0,
                "_resolution_hours": [],
            },
        )
        row["total_complaints"] += 1
        deadline = _naive_utc(complaint.sla_deadline)
        resolved_at = (
            _first_resolution_time(db, complaint.id)
            if complaint.status in (Status.RESOLVED, Status.CLOSED)
            else None
        )
        if resolved_at is not None:
            resolved_at = _naive_utc(resolved_at)
            created_at = _naive_utc(complaint.created_at)
            row["_resolved_count"] += 1
            row["_resolution_hours"].append(
                max(0, (resolved_at - created_at).total_seconds() / 3600)
            )
            if resolved_at <= deadline:
                row["resolved_within_sla"] += 1
            else:
                row["sla_breached_count"] += 1
        elif now >= deadline:
            row["sla_breached_count"] += 1

    reports = []
    for row in groups.values():
        resolved_count = row.pop("_resolved_count")
        durations = row.pop("_resolution_hours")
        row["sla_compliance_percent"] = (
            round(100 * row["resolved_within_sla"] / resolved_count, 2)
            if resolved_count
            else 0.0
        )
        row["average_resolution_time_hours"] = (
            round(sum(durations) / len(durations), 2) if durations else None
        )
        reports.append(row)
    reports.sort(
        key=lambda item: (
            item["category"].casefold(),
            item["department"].casefold(),
            item["priority"],
        )
    )
    return {
        "filters": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "category_id": category_id,
            "department": department,
        },
        "definition": (
            "SLA compliance = resolved complaints resolved on or before their SLA deadline "
            "divided by all resolved complaints with an SLA deadline."
        ),
        "reports": reports,
    }


@router.get("/sla-compliance")
def get_sla_compliance(
    start_date: date | None = None,
    end_date: date | None = None,
    category_id: int | None = Query(default=None, ge=1),
    department: str | None = Query(default=None, min_length=1, max_length=50),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    return build_sla_compliance_report(
        db, start_date, end_date, category_id, department
    )


@router.get("/sla-compliance/export")
def export_sla_compliance(
    format: str = Query(default="csv", pattern="^csv$"),
    start_date: date | None = None,
    end_date: date | None = None,
    category_id: int | None = Query(default=None, ge=1),
    department: str | None = Query(default=None, min_length=1, max_length=50),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    report = build_sla_compliance_report(
        db, start_date, end_date, category_id, department
    )
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(
        [
            "Category",
            "Total Complaints",
            "Priority",
            "Resolved Within SLA",
            "SLA Breached Count",
            "SLA Compliance %",
            "Average Resolution Time (hours)",
            "Department",
        ]
    )
    for row in report["reports"]:
        writer.writerow(
            [
                row["category"],
                row["total_complaints"],
                row["priority"],
                row["resolved_within_sla"],
                row["sla_breached_count"],
                row["sla_compliance_percent"],
                row["average_resolution_time_hours"],
                row["department"],
            ]
        )
    return Response(
        content=stream.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="sla-compliance-report.csv"'
        },
    )
