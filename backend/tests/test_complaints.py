from app.models import Complaint, Role
from app.security import hash_password


def create_test_user(db, email):
    from app.models import User

    user = User(
        name="Test Citizen",
        email=email,
        password_hash=hash_password("ValidStrong@123"),
        role=Role.COMPLAINANT,
    )
    db.add(user)
    db.commit()
    return user


def get_auth(client, email):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "ValidStrong@123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_create_complaint(client, db):
    create_test_user(db, "citizen1@example.com")
    headers = get_auth(client, "citizen1@example.com")

    response = client.post(
        "/complaints",
        json={
            "title": "Streetlight not working",
            "description": "Streetlight is not working near my house.",
            "category_id": None,
        },
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["reference_id"].startswith("CMP-")
    assert data["status"] == "New"
    assert data["complainant_id"] > 0


def test_reject_empty_title(client, db):
    create_test_user(db, "citizen2@example.com")
    headers = get_auth(client, "citizen2@example.com")

    response = client.post(
        "/complaints",
        json={
            "title": "   ",
            "description": "A valid complaint description.",
            "category_id": None,
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_reject_empty_description(client, db):
    create_test_user(db, "citizen3@example.com")
    headers = get_auth(client, "citizen3@example.com")

    response = client.post(
        "/complaints",
        json={
            "title": "Broken streetlight",
            "description": "   ",
            "category_id": None,
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_reject_duplicate_complaint(client, db):
    create_test_user(db, "citizen4@example.com")
    headers = get_auth(client, "citizen4@example.com")

    payload = {
        "title": "Garbage collection issue",
        "description": "Garbage has not been collected.",
        "category_id": None,
    }

    first = client.post("/complaints", json=payload, headers=headers)
    second = client.post("/complaints", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409


def test_reject_invalid_category(client, db):
    create_test_user(db, "citizen5@example.com")
    headers = get_auth(client, "citizen5@example.com")

    response = client.post(
        "/complaints",
        json={
            "title": "Water leakage",
            "description": "There is water leakage.",
            "category_id": 99999,
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_complaint_persistence(client, db):
    user = create_test_user(db, "citizen6@example.com")
    headers = get_auth(client, "citizen6@example.com")

    response = client.post(
        "/complaints",
        json={
            "title": "Road damage",
            "description": "There is a pothole on the road.",
            "category_id": None,
        },
        headers=headers,
    )

    assert response.status_code == 201

    saved = (
        db.query(Complaint)
        .filter(Complaint.reference_id == response.json()["reference_id"])
        .first()
    )

    assert saved is not None
    assert saved.complainant_id == user.id


def test_list_complaints(client, db):
    create_test_user(db, "citizen7@example.com")
    headers = get_auth(client, "citizen7@example.com")

    client.post(
        "/complaints",
        json={
            "title": "Damaged road",
            "description": "The road is damaged.",
            "category_id": None,
        },
        headers=headers,
    )

    response = client.get("/complaints", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_complaint_access_restricted(client, db):
    create_test_user(db, "owner@example.com")
    create_test_user(db, "other@example.com")

    owner_headers = get_auth(client, "owner@example.com")
    other_headers = get_auth(client, "other@example.com")

    created = client.post(
        "/complaints",
        json={
            "title": "Private complaint",
            "description": "This belongs to another citizen.",
            "category_id": None,
        },
        headers=owner_headers,
    )

    complaint_id = created.json()["id"]

    response = client.get(
        f"/complaints/{complaint_id}",
        headers=other_headers,
    )

    assert response.status_code == 403


def test_get_complaint_by_reference(client, db):
    create_test_user(db, "citizen8@example.com")
    headers = get_auth(client, "citizen8@example.com")

    created = client.post(
        "/complaints",
        json={
            "title": "Water supply issue",
            "description": "No water supply in the area.",
            "category_id": None,
        },
        headers=headers,
    )

    reference = created.json()["reference_id"]

    response = client.get(
        f"/complaints/reference/{reference}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["reference_id"] == reference


def test_complaints_require_authentication(client):
    response = client.get("/complaints")
    assert response.status_code == 401
