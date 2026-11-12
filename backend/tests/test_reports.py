from datetime import UTC, datetime, timedelta

from app.models import (
    AuditLog,
    Category,
    Complaint,
    Priority,
    Role,
    SLAStatus,
    Status,
)

from tests.conftest import auth_header, make_user


def add_complaint(db, citizen, reference, **overrides):
    values = {
        "reference_id": reference,
        "complainant_id": citizen.id,
        "title": "Streetlight repair",
        "description": "Synthetic test record for report coverage.",
    }
    values.update(overrides)
    row = Complaint(**values)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_dashboard_filters_metrics_and_role_access(client, db):
    admin = make_user(db, "reports-admin@example.com", Role.ADMIN)
    staff = make_user(db, "reports-staff@example.com", Role.STAFF, department="Water")
    citizen = make_user(db, "reports-citizen@example.com")
    outsider = make_user(db, "reports-outsider@example.com")
    water = Category(name="Water", department="Water", is_active=True)
    roads = Category(name="Roads", department="Transport", is_active=True)
    db.add_all([water, roads])
    db.commit()
    created = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
    complaint = add_complaint(
        db,
        citizen,
        "CMP-2026-810001",
        category_id=water.id,
        priority=Priority.HIGH,
        status=Status.RESOLVED,
        assignee_id=staff.id,
        created_at=created,
        sla_deadline=created + timedelta(hours=4),
        sla_status=SLAStatus.BREACHED,
    )
    db.add(
        AuditLog(
            complaint_id=complaint.id,
            actor_id=staff.id,
            action="STATUS_CHANGE",
            from_value=Status.IN_PROGRESS.value,
            to_value=Status.RESOLVED.value,
            timestamp=created + timedelta(hours=2),
        )
    )
    add_complaint(
        db,
        citizen,
        "CMP-2026-810002",
        category_id=roads.id,
        status=Status.NEW,
        created_at=created - timedelta(days=4),
    )
    db.commit()

    response = client.get(
        "/reports/dashboard",
        params={
            "start_date": created.date().isoformat(),
            "department": "water",
        },
        headers=auth_header(client, admin.email),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metrics"]["total_complaints"] == 1
    assert data["metrics"]["status_counts"]["Resolved"] == 1
    assert data["metrics"]["average_resolution_hours"] == 2.0
    assert data["metrics"]["sla_breach_rate_percent"] == 100.0
    assert data["category_distribution"] == [{"category": "Water", "count": 1}]
    assert data["priority_distribution"] == [{"priority": "High", "count": 1}]
    assert (
        client.get(
            "/reports/dashboard", headers=auth_header(client, outsider.email)
        ).status_code
        == 403
    )
    assert admin is not None


def test_empty_dashboard_and_invalid_date_range(client, db):
    admin = make_user(db, "empty-reports-admin@example.com", Role.ADMIN)
    headers = auth_header(client, admin.email)
    data = client.get("/reports/dashboard", headers=headers).json()
    assert data["metrics"]["total_complaints"] == 0
    assert data["metrics"]["sla_breach_rate_percent"] == 0.0
    assert data["metrics"]["average_resolution_hours"] is None
    invalid = client.get(
        "/reports/dashboard",
        params={"start_date": "2026-11-12", "end_date": "2026-11-01"},
        headers=headers,
    )
    assert invalid.status_code == 422


def test_csv_formula_safety_pdf_export_and_row_limit(client, db, monkeypatch):
    from app.routers import reports

    admin = make_user(db, "export-admin@example.com", Role.ADMIN)
    citizen = make_user(db, "export-citizen@example.com")
    add_complaint(
        db,
        citizen,
        "CMP-2026-820001",
        title='=HYPERLINK("https://example.invalid")',
        status=Status.NEW,
    )
    headers = auth_header(client, admin.email)
    csv_response = client.get("/reports/export?format=csv", headers=headers)
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "'=HYPERLINK" in csv_response.text
    pdf_response = client.get("/reports/export?format=pdf", headers=headers)
    assert pdf_response.status_code == 200
    assert pdf_response.content.startswith(b"%PDF-")

    add_complaint(db, citizen, "CMP-2026-820002", status=Status.NEW)
    monkeypatch.setattr(reports, "CSV_EXPORT_LIMIT", 1)
    capped = client.get("/reports/export?format=csv", headers=headers)
    assert capped.status_code == 413
