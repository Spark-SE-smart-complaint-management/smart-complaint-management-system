from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.models import AuditLog, Category, Complaint, Notification, Priority, Role, SLAStatus, Status
from app.services.sla import classify_sla, get_sla_timer
from tests.conftest import auth_header, make_user


def test_sla_classification_timezone_and_exact_deadline():
    created = datetime(2026, 11, 15, 9, 0, tzinfo=UTC)
    deadline = created + timedelta(hours=10)
    assert (
        classify_sla(created, deadline, created + timedelta(hours=7, minutes=59))
        == SLAStatus.ON_TRACK
    )
    assert (
        classify_sla(created, deadline, created + timedelta(hours=8))
        == SLAStatus.AT_RISK
    )
    assert (
        classify_sla(created, deadline, deadline - timedelta(microseconds=1))
        == SLAStatus.AT_RISK
    )
    assert classify_sla(created, deadline, deadline) == SLAStatus.BREACHED


def test_timer_handles_missing_deadline_and_pause():
    created = datetime(2026, 11, 15, 9, 0)
    untracked = SimpleNamespace(
        created_at=created, sla_deadline=None, sla_paused_at=None
    )
    assert get_sla_timer(untracked, created + timedelta(minutes=30)) == {
        "sla_elapsed_seconds": 1800,
        "sla_remaining_seconds": None,
        "sla_breach_state": "Not Tracked",
    }
    paused = SimpleNamespace(
        created_at=created,
        sla_deadline=created + timedelta(hours=2),
        sla_paused_at=created + timedelta(minutes=30),
    )
    result = get_sla_timer(paused, created + timedelta(hours=1))
    assert result["sla_elapsed_seconds"] == 1800
    assert result["sla_remaining_seconds"] == 5400
    assert result["sla_breach_state"] == "On Track"


def _complaint(db, citizen, category, ref, created, deadline, status):
    item = Complaint(
        reference_id=ref,
        complainant_id=citizen.id,
        title="Test complaint",
        description="SLA report fixture",
        category_id=category.id,
        priority=Priority.HIGH,
        status=status,
        created_at=created,
        sla_deadline=deadline,
        sla_status=SLAStatus.BREACHED
        if status == Status.RESOLVED
        else SLAStatus.ON_TRACK,
    )
    db.add(item)
    db.flush()
    return item


def test_sla_compliance_report_counts_and_filters(client, db):
    admin = make_user(db, "sla-report-admin@example.com", Role.ADMIN)
    staff = make_user(
        db, "sla-report-staff@example.com", Role.STAFF, department="Water"
    )
    citizen = make_user(db, "sla-report-citizen@example.com")
    category = Category(name="SLA Water", department="Water", is_active=True)
    db.add(category)
    db.commit()

    base = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
    on_time = _complaint(
        db,
        citizen,
        category,
        "CMP-SLA-000001",
        base,
        base + timedelta(hours=4),
        Status.RESOLVED,
    )
    late = _complaint(
        db,
        citizen,
        category,
        "CMP-SLA-000002",
        base,
        base + timedelta(hours=1),
        Status.RESOLVED,
    )
    _complaint(
        db,
        citizen,
        category,
        "CMP-SLA-000003",
        base,
        base + timedelta(minutes=1),
        Status.IN_PROGRESS,
    )
    for complaint, resolved_at in (
        (on_time, base + timedelta(hours=2)),
        (late, base + timedelta(hours=2)),
    ):
        db.add(
            AuditLog(
                complaint_id=complaint.id,
                actor_id=staff.id,
                action="STATUS_CHANGE",
                from_value=Status.IN_PROGRESS.value,
                to_value=Status.RESOLVED.value,
                timestamp=resolved_at,
            )
        )
    db.commit()

    headers = auth_header(client, admin.email)
    response = client.get(
        "/reports/sla-compliance", params={"department": "water"}, headers=headers
    )
    assert response.status_code == 200
    rows = response.json()["reports"]
    assert len(rows) == 1
    row = rows[0]
    assert row["total_complaints"] == 3
    assert row["resolved_within_sla"] == 1
    assert row["sla_breached_count"] == 2
    assert row["sla_compliance_percent"] == 50.0
    assert row["average_resolution_time_hours"] == 2.0

    exported = client.get("/reports/sla-compliance/export?format=csv", headers=headers)
    assert exported.status_code == 200
    assert "SLA Compliance %" in exported.text
    assert "SLA Water" in exported.text

    outsider = make_user(db, "sla-report-outsider@example.com")
    denied = client.get(
        "/reports/sla-compliance", headers=auth_header(client, outsider.email)
    )
    assert denied.status_code == 403


def test_business_hours_deadline_skips_weekends_and_configured_holidays(monkeypatch):
    from app.services.sla import _add_business_hours

    monkeypatch.setenv("SLA_BUSINESS_HOURS_ENABLED", "true")
    monkeypatch.setenv("SLA_TIMEZONE", "UTC")
    monkeypatch.setenv("SLA_WORKDAY_START", "09:00")
    monkeypatch.setenv("SLA_WORKDAY_END", "17:00")
    monkeypatch.setenv("SLA_WORKING_DAYS", "0,1,2,3,4")
    monkeypatch.setenv("SLA_HOLIDAYS", "2026-11-16")
    # Friday 16:00 + two business hours skips the holiday Monday.
    start = datetime(2026, 11, 13, 16, 0)
    assert _add_business_hours(start, 2) == datetime(2026, 11, 17, 10, 0)


def test_business_hours_disabled_preserves_calendar_hours(monkeypatch):
    from app.services.sla import _add_business_hours

    monkeypatch.setenv("SLA_BUSINESS_HOURS_ENABLED", "false")
    start = datetime(2026, 11, 13, 16, 0)
    assert _add_business_hours(start, 2) == datetime(2026, 11, 13, 18, 0)


def test_department_assigned_complaint_sends_warning_to_active_staff(db):
    from app.services.escalation import send_sla_warning

    staff_a = make_user(
        db, "sla-dept-a@example.com", Role.STAFF, department="Water"
    )
    staff_b = make_user(
        db, "sla-dept-b@example.com", Role.STAFF, department="Water"
    )
    make_user(db, "sla-dept-other@example.com", Role.STAFF, department="Roads")
    citizen = make_user(db, "sla-dept-citizen@example.com")
    category = Category(name="SLA Department Warning", department="Water", is_active=True)
    db.add(category)
    db.flush()
    complaint = Complaint(
        reference_id="CMP-SLA-DEPT-01",
        complainant_id=citizen.id,
        title="Department assigned",
        description="Warning recipient test",
        category_id=category.id,
        priority=Priority.HIGH,
        status=Status.ASSIGNED,
        assigned_department="Water",
        sla_deadline=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
        sla_status=SLAStatus.AT_RISK,
    )
    db.add(complaint)
    db.flush()

    assert send_sla_warning(db, complaint) is True
    db.commit()

    recipients = {
        row.user_id
        for row in db.query(Notification).filter_by(
            complaint_id=complaint.id,
            event_type="SLA_AT_RISK",
        ).all()
    }
    assert recipients == {staff_a.id, staff_b.id}
    assert send_sla_warning(db, complaint) is False
