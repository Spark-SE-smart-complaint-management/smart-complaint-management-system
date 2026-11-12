from app.models import Category, Priority, Role, SLAPolicy

from tests.conftest import auth_header, make_user


def test_citizen_to_resolution_reopen_and_report_flow(client, db):
    admin = make_user(db, "sprint2-admin@example.com", Role.ADMIN)
    staff = make_user(db, "sprint2-staff@example.com", Role.STAFF, department="Water")
    citizen = make_user(db, "sprint2-citizen@example.com")
    category = Category(name="Water Supply", department="Water", is_active=True)
    db.add(category)
    db.commit()
    db.add(
        SLAPolicy(
            category_id=category.id,
            priority=Priority.HIGH,
            duration_hours=24,
        )
    )
    db.commit()

    citizen_headers = auth_header(client, citizen.email)
    created = client.post(
        "/complaints",
        json={
            "title": "No water in building",
            "description": "Synthetic report: water service has stopped in our building.",
        },
        headers=citizen_headers,
    )
    assert created.status_code == 201
    complaint_id = created.json()["id"]
    admin_headers = auth_header(client, admin.email)
    staff_headers = auth_header(client, staff.email)

    classified = client.patch(
        f"/complaints/{complaint_id}/category",
        json={"category_id": category.id},
        headers=admin_headers,
    )
    assert classified.status_code == 200
    prioritized = client.patch(
        f"/complaints/{complaint_id}/priority",
        json={"priority": "High"},
        headers=admin_headers,
    )
    assert prioritized.status_code == 200
    assigned = client.post(
        f"/complaints/{complaint_id}/auto-assign",
        json={},
        headers=admin_headers,
    )
    assert assigned.status_code == 200
    assert assigned.json()["assignee_id"] == staff.id

    for status in ("In Progress", "Resolved", "Closed"):
        changed = client.patch(
            f"/complaints/{complaint_id}/status",
            json={"status": status, "reason": "Synthetic end-to-end validation."},
            headers=staff_headers,
        )
        assert changed.status_code == 200

    reopened = client.post(
        f"/complaints/{complaint_id}/reopen",
        params={"justification": "Synthetic demo verification after closure."},
        headers=citizen_headers,
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "Reopened"

    citizen_events = {
        item["event"]
        for item in client.get("/notifications", headers=citizen_headers).json()
    }
    staff_events = {
        item["event"]
        for item in client.get("/notifications", headers=staff_headers).json()
    }
    assert "COMPLAINT_SUBMITTED" in citizen_events
    assert "COMPLAINT_STATUS_CHANGED" in citizen_events
    assert "COMPLAINT_RESOLVED" in citizen_events
    assert "COMPLAINT_ASSIGNED" in staff_events

    dashboard = client.get("/reports/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200
    data = dashboard.json()
    assert data["metrics"]["total_complaints"] == 1
    assert data["metrics"]["status_counts"]["Reopened"] == 1
    assert data["category_distribution"] == [{"category": "Water Supply", "count": 1}]
    export = client.get("/reports/export?format=csv", headers=admin_headers)
    assert export.status_code == 200
    assert created.json()["reference_id"] in export.text
