import pytest

from app.models import Role, User
from app.security import hash_password


PDF_CONTENT = b"%PDF-1.4\nTest PDF content\n%%EOF"


@pytest.fixture()
def test_user(db):
    user = User(
        name="Test Complainant",
        email="complainant@test.com",
        password_hash=hash_password("ValidStrong@123"),
        role=Role.COMPLAINANT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def test_complaint(client, test_user):
    token = client.post(
        "/auth/login",
        json={
            "email": "complainant@test.com",
            "password": "ValidStrong@123",
        },
    ).json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/complaints",
        json={
            "title": "Test complaint",
            "description": "Complaint created for Issue 10 testing.",
            "category_id": None,
        },
        headers=headers,
    )

    assert response.status_code == 201

    return response.json(), headers


def test_create_comment(client, test_complaint):
    complaint, headers = test_complaint

    response = client.post(
        f"/complaints/{complaint['id']}/comments",
        json={"content": "This is a test comment."},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["content"] == "This is a test comment."
    assert response.json()["complaint_id"] == complaint["id"]


def test_list_comments(client, test_complaint):
    complaint, headers = test_complaint

    client.post(
        f"/complaints/{complaint['id']}/comments",
        json={"content": "First test comment"},
        headers=headers,
    )

    response = client.get(
        f"/complaints/{complaint['id']}/comments",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["content"] == "First test comment"


def test_reject_comment_from_unauthorized_user(
    client,
    db,
    test_complaint,
):
    complaint, _ = test_complaint

    other_user = User(
        name="Other User",
        email="other@test.com",
        password_hash=hash_password("ValidStrong@123"),
        role=Role.COMPLAINANT,
    )
    db.add(other_user)
    db.commit()

    token = client.post(
        "/auth/login",
        json={
            "email": "other@test.com",
            "password": "ValidStrong@123",
        },
    ).json()["access_token"]

    response = client.post(
        f"/complaints/{complaint['id']}/comments",
        json={"content": "Unauthorized comment"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_upload_and_download_attachment(
    client,
    test_complaint,
    monkeypatch,
    tmp_path,
):
    from app.services import attachment_service
    from app.routers import attachments

    monkeypatch.setattr(
        attachment_service,
        "UPLOAD_DIR",
        str(tmp_path),
    )
    monkeypatch.setattr(
        attachments,
        "UPLOAD_DIR",
        str(tmp_path),
    )

    complaint, headers = test_complaint

    upload_response = client.post(
        f"/complaints/{complaint['id']}/attachments",
        files={
            "files": (
                "test.pdf",
                PDF_CONTENT,
                "application/pdf",
            )
        },
        headers=headers,
    )

    assert upload_response.status_code == 201

    attachment = upload_response.json()["attachments"][0]
    assert attachment["original_filename"] == "test.pdf"

    download_response = client.get(
        f"/complaints/{complaint['id']}/attachments/{attachment['id']}",
        headers=headers,
    )

    assert download_response.status_code == 200
    assert download_response.content == PDF_CONTENT


def test_reject_unsupported_attachment(
    client,
    test_complaint,
):
    complaint, headers = test_complaint

    response = client.post(
        f"/complaints/{complaint['id']}/attachments",
        files={
            "files": (
                "malware.exe",
                b"test content",
                "application/octet-stream",
            )
        },
        headers=headers,
    )

    assert response.status_code == 400


def test_reject_attachment_with_invalid_signature(
    client,
    test_complaint,
):
    complaint, headers = test_complaint

    response = client.post(
        f"/complaints/{complaint['id']}/attachments",
        files={
            "files": (
                "fake.pdf",
                b"This is not a PDF file",
                "application/pdf",
            )
        },
        headers=headers,
    )

    assert response.status_code == 400


def test_reject_attachment_larger_than_10_mb(
    client,
    test_complaint,
):
    complaint, headers = test_complaint

    oversized_content = b"%PDF-1.4\n" + (b"A" * (10 * 1024 * 1024))

    response = client.post(
        f"/complaints/{complaint['id']}/attachments",
        files={
            "files": (
                "large.pdf",
                oversized_content,
                "application/pdf",
            )
        },
        headers=headers,
    )

    assert response.status_code == 413


def test_reject_more_than_five_attachments(
    client,
    test_complaint,
    monkeypatch,
    tmp_path,
):
    from app.services import attachment_service
    from app.routers import attachments

    monkeypatch.setattr(
        attachment_service,
        "UPLOAD_DIR",
        str(tmp_path),
    )
    monkeypatch.setattr(
        attachments,
        "UPLOAD_DIR",
        str(tmp_path),
    )

    complaint, headers = test_complaint

    files = [
        (
            "files",
            (f"test{i}.pdf", PDF_CONTENT, "application/pdf"),
        )
        for i in range(5)
    ]

    first_response = client.post(
        f"/complaints/{complaint['id']}/attachments",
        files=files,
        headers=headers,
    )

    assert first_response.status_code == 201

    sixth_response = client.post(
        f"/complaints/{complaint['id']}/attachments",
        files={
            "files": (
                "sixth.pdf",
                PDF_CONTENT,
                "application/pdf",
            )
        },
        headers=headers,
    )

    assert sixth_response.status_code == 400
