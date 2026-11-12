import pytest

from app.models import Role, User
from app import config
from app.security import hash_password, validate_password_strength, verify_password
from tests.conftest import auth_header, make_user

GOOD = {
    "name": "Test User",
    "email": "testuser@example.com",
    "phone": "9876543210",
    "password": "ValidStrong@123",
}


def test_register_success_hashes_password(client, db):
    r = client.post("/auth/register", json=GOOD)
    assert r.status_code == 201
    assert r.json()["role"] == "Complainant"
    user = db.query(User).filter_by(email=GOOD["email"]).one()
    assert user.password_hash != GOOD["password"] and user.password_hash.startswith(
        "$2"
    )


def test_register_duplicate_email(client):
    client.post("/auth/register", json=GOOD)
    assert client.post("/auth/register", json=GOOD).status_code == 409


def test_register_weak_password(client):
    assert (
        client.post("/auth/register", json={**GOOD, "password": "weak"}).status_code
        == 422
    )


def test_passwords_over_bcrypt_limit_are_rejected():
    too_long = "A1!" + "x" * 70
    assert "no more than 72 UTF-8 bytes" in validate_password_strength(too_long)
    assert verify_password(too_long, hash_password("ValidStrong@123")) is False


def test_production_requires_a_long_secret(monkeypatch):
    monkeypatch.setattr(config, "APP_ENV", "production")
    monkeypatch.setattr(config, "SECRET_KEY", "short")
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        config.validate_security_config()
    monkeypatch.setattr(config, "SECRET_KEY", "x" * 32)
    config.validate_security_config()


def test_register_invalid_email_and_blank_name(client):
    assert (
        client.post("/auth/register", json={**GOOD, "email": "nope"}).status_code == 422
    )
    assert client.post("/auth/register", json={**GOOD, "name": ""}).status_code == 422


def test_register_without_phone_ok(client):
    body = {k: v for k, v in GOOD.items() if k != "phone"}
    assert client.post("/auth/register", json=body).status_code == 201


def test_login_valid_and_wrong_password(client):
    client.post("/auth/register", json=GOOD)
    ok = client.post(
        "/auth/login", json={"email": GOOD["email"], "password": GOOD["password"]}
    )
    assert ok.status_code == 200 and "access_token" in ok.json()
    bad = client.post(
        "/auth/login", json={"email": GOOD["email"], "password": "Wrong@12345"}
    )
    assert bad.status_code == 401


def test_protected_endpoint_requires_token(client):
    assert client.get("/auth/me").status_code == 401
    assert (
        client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code
        == 401
    )


def test_rbac_complainant_cannot_list_users(client, db):
    make_user(db, "c@example.com")
    assert (
        client.get("/users", headers=auth_header(client, "c@example.com")).status_code
        == 403
    )


def test_admin_can_create_staff_and_change_role(client, db):
    make_user(db, "a@example.com", Role.ADMIN)
    h = auth_header(client, "a@example.com")
    r = client.post(
        "/users", headers=h, json={**GOOD, "role": "Staff", "department": "Technical"}
    )
    assert r.status_code == 201 and r.json()["role"] == "Staff"
    uid = r.json()["id"]
    r2 = client.patch(f"/users/{uid}", headers=h, json={"role": "Administrator"})
    assert r2.json()["role"] == "Administrator"


def test_deactivated_user_cannot_login(client, db):
    make_user(db, "a@example.com", Role.ADMIN)
    make_user(db, "x@example.com")
    uid = db.query(User).filter_by(email="x@example.com").one().id
    client.patch(
        f"/users/{uid}",
        headers=auth_header(client, "a@example.com"),
        json={"is_active": False},
    )
    r = client.post(
        "/auth/login", json={"email": "x@example.com", "password": "ValidStrong@123"}
    )
    assert r.status_code == 401
