"""Tests for issue #4 (REQ-12 to REQ-16)."""

import itertools
from datetime import datetime, timedelta, timezone

from app.models import AuditLog, Category, Complaint, Priority, Role, SLAPolicy, Status
from tests.conftest import auth_header, make_user

_ids = itertools.count(1)


def make_category(db, name, dept=None, active=True):
    c = Category(name=name, department=dept, is_active=active)
    db.add(c)
    db.commit()
    return c


def make_policy(db, category, priority, hours):
    p = SLAPolicy(category_id=category.id, priority=priority, duration_hours=hours)
    db.add(p)
    db.commit()
    return p


def make_complaint(db, complainant, **kw):
    c = Complaint(
        reference_id=f"CMP-2026-{next(_ids):06d}",
        complainant_id=complainant.id,
        title="Internet down",
        description="The internet has been down since morning.",
        **kw,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _dt(s):
    return datetime.fromisoformat(s)


def _naive(dt):
    return dt.replace(tzinfo=None)


def setup_world(db):
    admin = make_user(db, "admin@x.com", Role.ADMIN)
    staff = make_user(db, "staff@x.com", Role.STAFF)
    user = make_user(db, "user@x.com", Role.COMPLAINANT)
    return admin, staff, user


# ---------------- REQ-12: categories ----------------


def test_admin_creates_category(client, db):
    setup_world(db)
    r = client.post(
        "/categories",
        json={"name": "Billing", "department": "Finance"},
        headers=auth_header(client, "admin@x.com"),
    )
    assert r.status_code == 201
    assert r.json()["name"] == "Billing" and r.json()["is_active"] is True
    assert db.query(AuditLog).filter(AuditLog.action == "CATEGORY_CREATE").count() == 1


def test_duplicate_category_rejected_case_insensitive(client, db):
    setup_world(db)
    make_category(db, "Billing")
    r = client.post(
        "/categories",
        json={"name": "billing"},
        headers=auth_header(client, "admin@x.com"),
    )
    assert r.status_code == 409


def test_blank_category_name_rejected(client, db):
    setup_world(db)
    r = client.post(
        "/categories", json={"name": "   "}, headers=auth_header(client, "admin@x.com")
    )
    assert r.status_code == 422


def test_non_admin_cannot_create_or_update_category(client, db):
    setup_world(db)
    cat = make_category(db, "Billing")
    for email in ("staff@x.com", "user@x.com"):
        h = auth_header(client, email)
        assert (
            client.post("/categories", json={"name": "X"}, headers=h).status_code == 403
        )
        assert (
            client.patch(
                f"/categories/{cat.id}", json={"name": "Y"}, headers=h
            ).status_code
            == 403
        )


def test_unauthenticated_category_access_is_401(client, db):
    assert client.get("/categories").status_code == 401
    assert client.post("/categories", json={"name": "X"}).status_code == 401


def test_list_hides_inactive_except_for_admin_flag(client, db):
    setup_world(db)
    make_category(db, "Billing")
    make_category(db, "Old", active=False)
    user_h = auth_header(client, "user@x.com")
    assert [c["name"] for c in client.get("/categories", headers=user_h).json()] == [
        "Billing"
    ]
    assert (
        len(client.get("/categories?include_inactive=true", headers=user_h).json()) == 1
    )  # ignored for non-admin
    admin_h = auth_header(client, "admin@x.com")
    assert (
        len(client.get("/categories?include_inactive=true", headers=admin_h).json())
        == 2
    )


def test_admin_updates_and_deactivates_category(client, db):
    setup_world(db)
    cat = make_category(db, "Billing")
    h = auth_header(client, "admin@x.com")
    r = client.patch(
        f"/categories/{cat.id}",
        json={"is_active": False, "department": "Finance"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False and r.json()["department"] == "Finance"


def test_rename_to_existing_name_rejected(client, db):
    setup_world(db)
    make_category(db, "Billing")
    tech = make_category(db, "Technical")
    r = client.patch(
        f"/categories/{tech.id}",
        json={"name": "BILLING"},
        headers=auth_header(client, "admin@x.com"),
    )
    assert r.status_code == 409


def test_update_unknown_category_404(client, db):
    setup_world(db)
    r = client.patch(
        "/categories/999",
        json={"name": "Z"},
        headers=auth_header(client, "admin@x.com"),
    )
    assert r.status_code == 404


# ---------------- REQ-13: suggestion ----------------


def test_suggest_billing_from_text(client, db):
    setup_world(db)
    make_category(db, "Billing")
    make_category(db, "Technical")
    r = client.post(
        "/categories/suggest",
        json={"text": "I was overcharged on my bill, need a refund"},
        headers=auth_header(client, "user@x.com"),
    )
    assert r.status_code == 200
    assert r.json()["category"]["name"] == "Billing"


def test_suggest_technical_from_text(client, db):
    setup_world(db)
    make_category(db, "Billing")
    make_category(db, "Technical")
    r = client.post(
        "/categories/suggest",
        json={"text": "The internet connection is down"},
        headers=auth_header(client, "user@x.com"),
    )
    assert r.json()["category"]["name"] == "Technical"


def test_suggest_returns_null_when_no_match(client, db):
    setup_world(db)
    make_category(db, "Billing")
    r = client.post(
        "/categories/suggest",
        json={"text": "Hello there"},
        headers=auth_header(client, "user@x.com"),
    )
    assert r.status_code == 200 and r.json()["category"] is None


def test_suggest_ignores_inactive_category(client, db):
    setup_world(db)
    make_category(db, "Billing", active=False)
    r = client.post(
        "/categories/suggest",
        json={"text": "bill problem"},
        headers=auth_header(client, "user@x.com"),
    )
    assert r.json()["category"] is None


def test_suggest_does_not_change_complaint(client, db):
    admin, staff, user = setup_world(db)
    make_category(db, "Technical")
    c = make_complaint(db, user)
    r = client.get(
        f"/complaints/{c.id}/suggested-category",
        headers=auth_header(client, "staff@x.com"),
    )
    assert r.status_code == 200 and r.json()["category"]["name"] == "Technical"
    db.refresh(c)
    assert c.category_id is None


def test_suggest_endpoint_needs_staff_role(client, db):
    admin, staff, user = setup_world(db)
    c = make_complaint(db, user)
    r = client.get(
        f"/complaints/{c.id}/suggested-category",
        headers=auth_header(client, "user@x.com"),
    )
    assert r.status_code == 403


# ---------------- REQ-15: SLA policy ----------------


def test_admin_creates_then_updates_policy_same_row(client, db):
    setup_world(db)
    cat = make_category(db, "Technical")
    h = auth_header(client, "admin@x.com")
    body = {"category_id": cat.id, "priority": "High", "duration_hours": 4}
    first = client.put("/sla-policies", json=body, headers=h)
    assert first.status_code == 200 and first.json()["duration_hours"] == 4
    second = client.put("/sla-policies", json={**body, "duration_hours": 6}, headers=h)
    assert (
        second.json()["id"] == first.json()["id"]
        and second.json()["duration_hours"] == 6
    )
    assert db.query(SLAPolicy).count() == 1


def test_policy_validation(client, db):
    setup_world(db)
    cat = make_category(db, "Technical")
    h = auth_header(client, "admin@x.com")
    assert (
        client.put(
            "/sla-policies",
            json={"category_id": cat.id, "priority": "High", "duration_hours": 0},
            headers=h,
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/sla-policies",
            json={"category_id": cat.id, "priority": "Urgent", "duration_hours": 4},
            headers=h,
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/sla-policies",
            json={"category_id": 999, "priority": "High", "duration_hours": 4},
            headers=h,
        ).status_code
        == 404
    )


def test_only_admin_changes_policy_but_staff_can_read(client, db):
    admin, staff, user = setup_world(db)
    cat = make_category(db, "Technical")
    make_policy(db, cat, Priority.HIGH, 4)
    body = {"category_id": cat.id, "priority": "High", "duration_hours": 1}
    assert (
        client.put(
            "/sla-policies", json=body, headers=auth_header(client, "staff@x.com")
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/sla-policies", headers=auth_header(client, "staff@x.com")
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/sla-policies", headers=auth_header(client, "user@x.com")
        ).status_code
        == 403
    )


def test_admin_deletes_policy(client, db):
    setup_world(db)
    cat = make_category(db, "Technical")
    p = make_policy(db, cat, Priority.HIGH, 4)
    h = auth_header(client, "admin@x.com")
    assert client.delete(f"/sla-policies/{p.id}", headers=h).status_code == 204
    assert client.delete(f"/sla-policies/{p.id}", headers=h).status_code == 404


# ---------------- REQ-14 + REQ-16: priority and deadline recompute ----------------


def test_staff_sets_priority_and_deadline_is_computed(client, db):
    admin, staff, user = setup_world(db)
    cat = make_category(db, "Technical")
    make_policy(db, cat, Priority.HIGH, 4)
    c = make_complaint(db, user, category_id=cat.id)
    r = client.patch(
        f"/complaints/{c.id}/priority",
        json={"priority": "High"},
        headers=auth_header(client, "staff@x.com"),
    )
    assert r.status_code == 200
    assert r.json()["priority"] == "High"
    assert _dt(r.json()["sla_deadline"]) == _naive(c.created_at) + timedelta(hours=4)
    assert r.json()["sla_status"] == "On Track"


def test_priority_change_recomputes_deadline(client, db):
    admin, staff, user = setup_world(db)
    cat = make_category(db, "Technical")
    make_policy(db, cat, Priority.HIGH, 4)
    make_policy(db, cat, Priority.CRITICAL, 2)
    c = make_complaint(db, user, category_id=cat.id, priority=Priority.HIGH)
    h = auth_header(client, "staff@x.com")
    client.patch(f"/complaints/{c.id}/priority", json={"priority": "High"}, headers=h)
    r = client.patch(
        f"/complaints/{c.id}/priority", json={"priority": "Critical"}, headers=h
    )
    assert _dt(r.json()["sla_deadline"]) == _naive(c.created_at) + timedelta(hours=2)


def test_category_change_recomputes_deadline(client, db):
    admin, staff, user = setup_world(db)
    tech = make_category(db, "Technical")
    bill = make_category(db, "Billing")
    make_policy(db, tech, Priority.HIGH, 4)
    make_policy(db, bill, Priority.HIGH, 24)
    c = make_complaint(db, user, category_id=tech.id, priority=Priority.HIGH)
    r = client.patch(
        f"/complaints/{c.id}/category",
        json={"category_id": bill.id},
        headers=auth_header(client, "staff@x.com"),
    )
    assert r.status_code == 200 and r.json()["category_id"] == bill.id
    assert _dt(r.json()["sla_deadline"]) == _naive(c.created_at) + timedelta(hours=24)


def test_deadline_is_none_when_no_policy_or_no_priority(client, db):
    admin, staff, user = setup_world(db)
    cat = make_category(db, "Technical")
    c = make_complaint(db, user)
    h = auth_header(client, "staff@x.com")
    r = client.patch(
        f"/complaints/{c.id}/category", json={"category_id": cat.id}, headers=h
    )
    assert r.json()["sla_deadline"] is None  # category set, but no priority yet
    r = client.patch(
        f"/complaints/{c.id}/priority", json={"priority": "Low"}, headers=h
    )
    assert r.json()["sla_deadline"] is None  # priority set, but no policy configured


def test_past_deadline_is_marked_breached(client, db):
    admin, staff, user = setup_world(db)
    cat = make_category(db, "Technical")
    make_policy(db, cat, Priority.HIGH, 4)
    c = make_complaint(
        db,
        user,
        category_id=cat.id,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        - timedelta(hours=10),
    )
    r = client.patch(
        f"/complaints/{c.id}/priority",
        json={"priority": "High"},
        headers=auth_header(client, "staff@x.com"),
    )
    assert r.json()["sla_status"] == "Breached"


def test_at_risk_after_80_percent_elapsed(client, db):
    admin, staff, user = setup_world(db)
    cat = make_category(db, "Technical")
    make_policy(db, cat, Priority.HIGH, 10)
    c = make_complaint(
        db,
        user,
        category_id=cat.id,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=9),
    )
    r = client.patch(
        f"/complaints/{c.id}/priority",
        json={"priority": "High"},
        headers=auth_header(client, "staff@x.com"),
    )
    assert r.json()["sla_status"] == "At Risk"


def test_recompute_resets_warning_flag(client, db):
    admin, staff, user = setup_world(db)
    cat = make_category(db, "Technical")
    make_policy(db, cat, Priority.HIGH, 4)
    c = make_complaint(db, user, category_id=cat.id, sla_warning_sent=True)
    client.patch(
        f"/complaints/{c.id}/priority",
        json={"priority": "High"},
        headers=auth_header(client, "staff@x.com"),
    )
    db.refresh(c)
    assert c.sla_warning_sent is False


def test_invalid_priority_rejected(client, db):
    admin, staff, user = setup_world(db)
    c = make_complaint(db, user)
    r = client.patch(
        f"/complaints/{c.id}/priority",
        json={"priority": "Urgent"},
        headers=auth_header(client, "staff@x.com"),
    )
    assert r.status_code == 422


def test_unknown_or_inactive_category_rejected(client, db):
    admin, staff, user = setup_world(db)
    old = make_category(db, "Old", active=False)
    c = make_complaint(db, user)
    h = auth_header(client, "staff@x.com")
    assert (
        client.patch(
            f"/complaints/{c.id}/category", json={"category_id": 999}, headers=h
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/complaints/{c.id}/category", json={"category_id": old.id}, headers=h
        ).status_code
        == 422
    )


def test_unknown_complaint_404(client, db):
    setup_world(db)
    r = client.patch(
        "/complaints/999/priority",
        json={"priority": "High"},
        headers=auth_header(client, "staff@x.com"),
    )
    assert r.status_code == 404


def test_complainant_cannot_set_priority_or_category(client, db):
    admin, staff, user = setup_world(db)
    cat = make_category(db, "Technical")
    c = make_complaint(db, user)
    h = auth_header(client, "user@x.com")
    assert (
        client.patch(
            f"/complaints/{c.id}/priority", json={"priority": "High"}, headers=h
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/complaints/{c.id}/category", json={"category_id": cat.id}, headers=h
        ).status_code
        == 403
    )


def test_staff_blocked_on_complaint_assigned_to_someone_else(client, db):
    admin, staff, user = setup_world(db)
    other = make_user(db, "other@x.com", Role.STAFF)
    c = make_complaint(db, user, assignee_id=other.id)
    r = client.patch(
        f"/complaints/{c.id}/priority",
        json={"priority": "High"},
        headers=auth_header(client, "staff@x.com"),
    )
    assert r.status_code == 403
    r = client.patch(
        f"/complaints/{c.id}/priority",
        json={"priority": "High"},
        headers=auth_header(client, "admin@x.com"),
    )
    assert r.status_code == 200  # admin may triage any complaint


def test_assigned_staff_can_triage_own_complaint(client, db):
    admin, staff, user = setup_world(db)
    c = make_complaint(db, user, assignee_id=staff.id)
    r = client.patch(
        f"/complaints/{c.id}/priority",
        json={"priority": "Low"},
        headers=auth_header(client, "staff@x.com"),
    )
    assert r.status_code == 200


def test_closed_complaint_cannot_be_retriaged(client, db):
    admin, staff, user = setup_world(db)
    c = make_complaint(db, user, status=Status.CLOSED)
    r = client.patch(
        f"/complaints/{c.id}/priority",
        json={"priority": "High"},
        headers=auth_header(client, "admin@x.com"),
    )
    assert r.status_code == 409


def test_priority_change_is_audited(client, db):
    admin, staff, user = setup_world(db)
    cat = make_category(db, "Technical")
    make_policy(db, cat, Priority.HIGH, 4)
    c = make_complaint(db, user, category_id=cat.id, priority=Priority.LOW)
    client.patch(
        f"/complaints/{c.id}/priority",
        json={"priority": "High"},
        headers=auth_header(client, "staff@x.com"),
    )
    row = (
        db.query(AuditLog)
        .filter(AuditLog.action == "PRIORITY_CHANGE", AuditLog.complaint_id == c.id)
        .one()
    )
    assert (row.from_value, row.to_value, row.actor_id) == ("Low", "High", staff.id)
    assert (
        db.query(AuditLog)
        .filter(AuditLog.action == "SLA_RECOMPUTE", AuditLog.complaint_id == c.id)
        .count()
        == 1
    )
