
from datetime import datetime, timedelta, timezone

from app.models import AuditLog, Complaint, Role, Status, User
from app.security import hash_password
from app.services.audit import log_action


# --------------------------------------------------
# Test helpers
# --------------------------------------------------

def make_user(db, email, role=Role.COMPLAINANT):
    user = User(
        name="Test User",
        email=email,
        password_hash=hash_password("ValidStrong@123"),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_header(client, email):
    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "ValidStrong@123",
        },
    )
    assert response.status_code == 200
    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


def create_complaint(db, complainant, assignee=None, status=Status.NEW):
    complaint = Complaint(
        reference_id="CMP-2026-000123",
        complainant_id=complainant.id,
        title="Water supply issue",
        description=(
            "There has been no water supply in our area "
            "for several days."
        ),
        status=status,
        assignee_id=assignee.id if assignee else None,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


def create_closure_log(db, complaint, staff, closed_at=None):
    log_action(
        db,
        action="STATUS_CHANGE",
        complaint_id=complaint.id,
        actor_id=staff.id,
        from_value=Status.RESOLVED.value,
        to_value=Status.CLOSED.value,
        trigger_type="Manual",
        reason="Complaint resolved and closed",
    )

    db.flush()

    entry = (
        db.query(AuditLog)
        .filter(
            AuditLog.complaint_id == complaint.id,
            AuditLog.action == "STATUS_CHANGE",
            AuditLog.to_value == Status.CLOSED.value,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )

    if closed_at is not None:
        entry.timestamp = closed_at

    db.commit()


def close_again(db, complaint, staff):
    old_status = complaint.status
    complaint.status = Status.CLOSED

    log_action(
        db,
        action="STATUS_CHANGE",
        complaint_id=complaint.id,
        actor_id=staff.id,
        from_value=old_status.value,
        to_value=Status.CLOSED.value,
        trigger_type="Manual",
        reason="Complaint closed again",
    )
    db.commit()


# --------------------------------------------------
# Status transition tests
# --------------------------------------------------

def test_assigned_staff_can_update_status(client, db):
    citizen = make_user(db, "citizen1@example.com")
    staff = make_user(db, "staff1@example.com", Role.STAFF)

    complaint = create_complaint(db, citizen, staff)

    response = client.patch(
        f"/complaints/{complaint.id}/status",
        json={
            "status": "In Progress",
            "reason": "Investigation started",
        },
        headers=auth_header(client, staff.email),
    )

    assert response.status_code == 200
    assert response.json()["new_status"] == "In Progress"


def test_unassigned_staff_cannot_update_status(client, db):
    citizen = make_user(db, "citizen2@example.com")
    assigned_staff = make_user(
        db, "staff2@example.com", Role.STAFF
    )
    other_staff = make_user(
        db, "staff3@example.com", Role.STAFF
    )

    complaint = create_complaint(db, citizen, assigned_staff)

    response = client.patch(
        f"/complaints/{complaint.id}/status",
        json={"status": "In Progress"},
        headers=auth_header(client, other_staff.email),
    )

    assert response.status_code == 403


def test_invalid_status_transition_is_rejected(client, db):
    citizen = make_user(db, "citizen4@example.com")
    staff = make_user(db, "staff4@example.com", Role.STAFF)

    complaint = create_complaint(db, citizen, staff)

    response = client.patch(
        f"/complaints/{complaint.id}/status",
        json={"status": "Closed"},
        headers=auth_header(client, staff.email),
    )

    assert response.status_code == 409


# --------------------------------------------------
# History visibility tests
# --------------------------------------------------

def test_complainant_can_view_own_history(client, db):
    citizen = make_user(db, "citizen5@example.com")
    staff = make_user(db, "staff5@example.com", Role.STAFF)

    complaint = create_complaint(db, citizen, staff)

    log_action(
        db,
        action="STATUS_CHANGE",
        complaint_id=complaint.id,
        actor_id=staff.id,
        from_value=Status.NEW.value,
        to_value=Status.ASSIGNED.value,
        trigger_type="Manual",
    )
    db.commit()

    response = client.get(
        f"/complaints/{complaint.id}/history",
        headers=auth_header(client, citizen.email),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["to_value"] == "Assigned"


def test_complainant_cannot_view_another_complaints_history(
    client, db
):
    citizen1 = make_user(db, "citizen6@example.com")
    citizen2 = make_user(db, "citizen7@example.com")
    staff = make_user(db, "staff6@example.com", Role.STAFF)

    complaint = create_complaint(db, citizen1, staff)

    response = client.get(
        f"/complaints/{complaint.id}/history",
        headers=auth_header(client, citizen2.email),
    )

    assert response.status_code == 403


# --------------------------------------------------
# First reopening tests
# --------------------------------------------------

def test_complainant_can_reopen_within_grace_period(client, db):
    citizen = make_user(db, "citizen8@example.com")
    staff = make_user(db, "staff8@example.com", Role.STAFF)

    complaint = create_complaint(
        db, citizen, staff, Status.CLOSED
    )
    create_closure_log(db, complaint, staff)

    response = client.post(
        f"/complaints/{complaint.id}/reopen",
        params={
            "justification": "The issue has started again."
        },
        headers=auth_header(client, citizen.email),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Reopened"


def test_reopening_after_grace_period_is_rejected(client, db):
    citizen = make_user(db, "citizen9@example.com")
    staff = make_user(db, "staff9@example.com", Role.STAFF)

    complaint = create_complaint(
        db, citizen, staff, Status.CLOSED
    )

    old_closure = datetime.now(timezone.utc) - timedelta(days=8)
    create_closure_log(db, complaint, staff, old_closure)

    response = client.post(
        f"/complaints/{complaint.id}/reopen",
        params={
            "justification": "The issue has started again."
        },
        headers=auth_header(client, citizen.email),
    )

    assert response.status_code == 409


# --------------------------------------------------
# Administrator approval tests
# --------------------------------------------------

def test_second_reopen_requires_admin_approval(client, db):
    citizen = make_user(db, "citizen10@example.com")
    staff = make_user(db, "staff10@example.com", Role.STAFF)

    complaint = create_complaint(
        db, citizen, staff, Status.CLOSED
    )
    create_closure_log(db, complaint, staff)

    citizen_headers = auth_header(client, citizen.email)

    # First reopening is directly allowed.
    first_response = client.post(
        f"/complaints/{complaint.id}/reopen",
        params={
            "justification": "The issue has started again."
        },
        headers=citizen_headers,
    )

    assert first_response.status_code == 200

    # Simulate staff closing the complaint again.
    close_again(db, complaint, staff)

    # Second reopening must wait for administrator approval.
    second_response = client.post(
        f"/complaints/{complaint.id}/reopen",
        params={
            "justification": "The same issue has returned again."
        },
        headers=citizen_headers,
    )

    assert second_response.status_code == 202
    assert second_response.json()["status"] == "Pending Approval"

    # Complaint remains closed until approval.
    db.refresh(complaint)
    assert complaint.status == Status.CLOSED


def test_admin_can_approve_second_reopen_request(client, db):
    citizen = make_user(db, "citizen11@example.com")
    staff = make_user(db, "staff11@example.com", Role.STAFF)
    admin = make_user(db, "admin11@example.com", Role.ADMIN)

    complaint = create_complaint(
        db, citizen, staff, Status.CLOSED
    )
    create_closure_log(db, complaint, staff)

    citizen_headers = auth_header(client, citizen.email)

    # First reopening.
    first_response = client.post(
        f"/complaints/{complaint.id}/reopen",
        params={
            "justification": "The issue has started again."
        },
        headers=citizen_headers,
    )
    assert first_response.status_code == 200

    # Close again and request a second reopening.
    close_again(db, complaint, staff)

    second_response = client.post(
        f"/complaints/{complaint.id}/reopen",
        params={
            "justification": "The problem has returned again."
        },
        headers=citizen_headers,
    )
    assert second_response.status_code == 202

    # Administrator approves.
    approval_response = client.post(
        f"/complaints/{complaint.id}/reopen/approve",
        headers=auth_header(client, admin.email),
    )

    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == "Reopened"

    db.refresh(complaint)
    assert complaint.status == Status.REOPENED


def test_staff_cannot_approve_reopen_request(client, db):
    citizen = make_user(db, "citizen12@example.com")
    staff = make_user(db, "staff12@example.com", Role.STAFF)

    complaint = create_complaint(
        db, citizen, staff, Status.CLOSED
    )

    response = client.post(
        f"/complaints/{complaint.id}/reopen/approve",
        headers=auth_header(client, staff.email),
    )

    assert response.status_code == 403


def test_admin_cannot_approve_without_pending_request(client, db):
    citizen = make_user(db, "citizen13@example.com")
    admin = make_user(db, "admin13@example.com", Role.ADMIN)

    complaint = create_complaint(
        db, citizen, status=Status.CLOSED
    )

    response = client.post(
        f"/complaints/{complaint.id}/reopen/approve",
        headers=auth_header(client, admin.email),
    )

    assert response.status_code == 404
