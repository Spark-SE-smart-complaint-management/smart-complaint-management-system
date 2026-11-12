from app.models import AuditLog, Category, Complaint, Notification, Role, Status
from tests.conftest import auth_header, make_user


def make_complaint(db, citizen, **kwargs):
    complaint = Complaint(
        reference_id=f"CMP-2026-{db.query(Complaint).count() + 1:06d}",
        complainant_id=citizen.id,
        title="Water supply issue",
        description="There is no water supply in our area.",
        **kwargs,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


def admin_headers(client, db):
    make_user(db, "assignment-admin@example.com", Role.ADMIN)
    return auth_header(client, "assignment-admin@example.com")


def test_admin_assigns_complaint_to_staff(client, db):
    headers = admin_headers(client, db)
    citizen = make_user(db, "assign-citizen@example.com")
    staff = make_user(db, "assign-staff@example.com", Role.STAFF, department="Water")
    complaint = make_complaint(db, citizen)

    response = client.post(
        f"/complaints/{complaint.id}/assign",
        json={"staff_id": staff.id},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["assignee_id"] == staff.id
    assert response.json()["status"] == "Assigned"
    db.refresh(complaint)
    assert complaint.assignee_id == staff.id
    assert db.query(Notification).filter_by(user_id=staff.id, event="COMPLAINT_ASSIGNED").count() == 1
    log = db.query(AuditLog).filter_by(complaint_id=complaint.id, action="COMPLAINT_ASSIGNED").one()
    assert log.to_value == f"user:{staff.id}"


def test_admin_assigns_complaint_to_department(client, db):
    headers = admin_headers(client, db)
    citizen = make_user(db, "dept-citizen@example.com")
    first = make_user(db, "dept-staff1@example.com", Role.STAFF, department="Water")
    second = make_user(db, "dept-staff2@example.com", Role.STAFF, department="Water")
    complaint = make_complaint(db, citizen)

    response = client.post(
        f"/complaints/{complaint.id}/assign",
        json={"department": "Water"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["assigned_department"] == "Water"
    assert response.json()["assignee_id"] is None
    assert db.query(Notification).filter(
        Notification.user_id.in_([first.id, second.id]),
        Notification.event == "COMPLAINT_ASSIGNED",
    ).count() == 2


def test_reassignment_requires_reason_and_records_old_and_new_owner(client, db):
    headers = admin_headers(client, db)
    citizen = make_user(db, "reason-citizen@example.com")
    first = make_user(db, "reason-staff1@example.com", Role.STAFF, department="Water")
    second = make_user(db, "reason-staff2@example.com", Role.STAFF, department="Water")
    complaint = make_complaint(db, citizen, assignee_id=first.id, status=Status.ASSIGNED)

    rejected = client.post(
        f"/complaints/{complaint.id}/assign",
        json={"staff_id": second.id},
        headers=headers,
    )
    assert rejected.status_code == 422

    accepted = client.post(
        f"/complaints/{complaint.id}/assign",
        json={"staff_id": second.id, "reason": "Original staff member is unavailable."},
        headers=headers,
    )
    assert accepted.status_code == 200
    log = db.query(AuditLog).filter_by(complaint_id=complaint.id, action="COMPLAINT_REASSIGNED").one()
    assert log.from_value == f"user:{first.id}"
    assert log.to_value == f"user:{second.id}"
    assert log.reason == "Original staff member is unavailable."


def test_auto_assignment_chooses_least_loaded_staff_in_category_department(client, db):
    headers = admin_headers(client, db)
    citizen = make_user(db, "auto-citizen@example.com")
    low_load = make_user(db, "auto-low@example.com", Role.STAFF, department="Water")
    high_load = make_user(db, "auto-high@example.com", Role.STAFF, department="Water")
    category = Category(name="Water", department="Water", is_active=True)
    db.add(category)
    db.commit()
    # Give the second staff member two active complaints.
    make_complaint(db, citizen, assignee_id=high_load.id, status=Status.ASSIGNED)
    make_complaint(db, citizen, assignee_id=high_load.id, status=Status.IN_PROGRESS)
    target = make_complaint(db, citizen, category_id=category.id)

    response = client.post(f"/complaints/{target.id}/auto-assign", json={}, headers=headers)

    assert response.status_code == 200
    assert response.json()["assignee_id"] == low_load.id
    log = db.query(AuditLog).filter_by(complaint_id=target.id, action="COMPLAINT_ASSIGNED").one()
    assert log.trigger_type == "Automatic"


def test_auto_assignment_breaks_ties_by_user_id(client, db):
    headers = admin_headers(client, db)
    citizen = make_user(db, "tie-citizen@example.com")
    first = make_user(db, "tie-first@example.com", Role.STAFF, department="Roads")
    make_user(db, "tie-second@example.com", Role.STAFF, department="Roads")
    category = Category(name="Roads", department="Roads", is_active=True)
    db.add(category)
    db.commit()
    target = make_complaint(db, citizen, category_id=category.id)

    response = client.post(f"/complaints/{target.id}/auto-assign", json={}, headers=headers)

    assert response.status_code == 200
    assert response.json()["assignee_id"] == first.id


def test_non_admin_cannot_assign_complaints(client, db):
    citizen = make_user(db, "nonadmin-citizen@example.com")
    staff = make_user(db, "nonadmin-staff@example.com", Role.STAFF, department="Water")
    complaint = make_complaint(db, citizen)
    staff_headers = auth_header(client, staff.email)

    response = client.post(
        f"/complaints/{complaint.id}/assign",
        json={"staff_id": staff.id},
        headers=staff_headers,
    )
    assert response.status_code == 403


def test_assign_rejects_inactive_or_non_staff_user(client, db):
    headers = admin_headers(client, db)
    citizen = make_user(db, "invalid-citizen@example.com")
    inactive = make_user(db, "inactive-staff@example.com", Role.STAFF, department="Water", is_active=False)
    complaint = make_complaint(db, citizen)

    response = client.post(
        f"/complaints/{complaint.id}/assign",
        json={"staff_id": inactive.id},
        headers=headers,
    )
    assert response.status_code == 422


def test_assignment_rejects_resolved_complaint(client, db):
    headers = admin_headers(client, db)
    citizen = make_user(db, "closed-citizen@example.com")
    staff = make_user(db, "closed-staff@example.com", Role.STAFF, department="Water")
    complaint = make_complaint(db, citizen, status=Status.RESOLVED)

    response = client.post(
        f"/complaints/{complaint.id}/assign",
        json={"staff_id": staff.id},
        headers=headers,
    )
    assert response.status_code == 409


def test_complainant_history_includes_assignment_and_reassignment(client, db):
    headers = admin_headers(client, db)
    citizen = make_user(db, "history-citizen@example.com")
    first = make_user(db, "history-staff1@example.com", Role.STAFF, department="Water")
    second = make_user(db, "history-staff2@example.com", Role.STAFF, department="Water")
    complaint = make_complaint(db, citizen)

    client.post(
        f"/complaints/{complaint.id}/assign",
        json={"staff_id": first.id},
        headers=headers,
    )
    client.post(
        f"/complaints/{complaint.id}/assign",
        json={"staff_id": second.id, "reason": "Workload balancing."},
        headers=headers,
    )

    response = client.get(
        f"/complaints/{complaint.id}/history",
        headers=auth_header(client, citizen.email),
    )

    assert response.status_code == 200
    actions = [row["action"] for row in response.json()]
    assert actions == ["COMPLAINT_ASSIGNED", "COMPLAINT_REASSIGNED"]
    assert response.json()[1]["reason"] == "Workload balancing."
