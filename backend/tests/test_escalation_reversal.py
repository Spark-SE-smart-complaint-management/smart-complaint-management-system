from datetime import UTC, datetime, timedelta

from app.models import (
    AuditLog,
    Category,
    Complaint,
    EscalationHierarchy,
    Priority,
    Role,
    Status,
)
from app.services.escalation import escalate_complaint
from tests.conftest import auth_header, make_user


def test_admin_can_reverse_automatic_escalation_and_audit_it(client, db):
    admin = make_user(db, "reverse-admin@example.com", Role.ADMIN)
    previous_staff = make_user(
        db, "reverse-old-staff@example.com", Role.STAFF, department="Water"
    )
    next_staff = make_user(
        db, "reverse-next-staff@example.com", Role.STAFF, department="Water"
    )
    citizen = make_user(db, "reverse-citizen@example.com")
    category = Category(name="Reverse Test Water", department="Water", is_active=True)
    db.add(category)
    db.flush()

    db.add(
        EscalationHierarchy(
            category_id=category.id,
            level=1,
            assignee_id=next_staff.id,
            role_name="Senior Officer",
            is_active=True,
        )
    )
    complaint = Complaint(
        reference_id="CMP-REV-000001",
        complainant_id=citizen.id,
        title="Reverse test",
        description="Automatic escalation reversal",
        category_id=category.id,
        priority=Priority.HIGH,
        status=Status.IN_PROGRESS,
        assignee_id=previous_staff.id,
        sla_deadline=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1),
        escalation_level=0,
    )
    db.add(complaint)
    db.commit()

    assert escalate_complaint(db, complaint, trigger_type="Automatic") is True
    db.commit()
    assert complaint.status == Status.ESCALATED
    assert complaint.assignee_id == next_staff.id
    escalation_event = (
        db.query(AuditLog)
        .filter_by(complaint_id=complaint.id, action="COMPLAINT_ESCALATED")
        .one()
    )

    response = client.post(
        f"/escalation-hierarchy/complaints/{complaint.id}/reverse",
        json={"reason": "Incorrect automatic escalation"},
        headers=auth_header(client, admin.email),
    )
    assert response.status_code == 200
    assert response.json()["status"] == Status.IN_PROGRESS.value
    assert response.json()["escalation_level"] == 0
    assert response.json()["assignee_id"] == previous_staff.id

    db.refresh(complaint)
    assert complaint.status == Status.IN_PROGRESS
    assert complaint.assignee_id == previous_staff.id
    reversal = (
        db.query(AuditLog)
        .filter_by(
            complaint_id=complaint.id,
            action="COMPLAINT_ESCALATION_REVERSED",
        )
        .one()
    )
    assert reversal.actor_id == admin.id
    assert reversal.from_value == str(escalation_event.id)
    assert reversal.reason and "Incorrect automatic escalation" in reversal.reason

    duplicate = client.post(
        f"/escalation-hierarchy/complaints/{complaint.id}/reverse",
        json={"reason": "Trying again"},
        headers=auth_header(client, admin.email),
    )
    assert duplicate.status_code == 409


def test_only_admin_can_reverse_automatic_escalation(client, db):
    staff = make_user(db, "reverse-denied-staff@example.com", Role.STAFF)
    citizen = make_user(db, "reverse-denied-citizen@example.com")
    category = Category(name="Reverse Auth Test", department="Water", is_active=True)
    db.add(category)
    db.flush()
    complaint = Complaint(
        reference_id="CMP-REV-000002",
        complainant_id=citizen.id,
        title="Reverse authorization test",
        description="Only administrators may reverse escalations",
        category_id=category.id,
        priority=Priority.HIGH,
        status=Status.IN_PROGRESS,
        sla_deadline=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1),
    )
    db.add(complaint)
    db.commit()

    response = client.post(
        f"/escalation-hierarchy/complaints/{complaint.id}/reverse",
        json={"reason": "Unauthorized attempt"},
        headers=auth_header(client, staff.email),
    )
    assert response.status_code == 403
