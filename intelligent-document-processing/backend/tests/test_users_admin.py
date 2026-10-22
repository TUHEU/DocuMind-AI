import pytest

from app.models import AuditEvent, User
from tests.conftest import auth_header, make_user

NEW = {"email": "rev@example.com", "full_name": "Rita Rev", "password": "Passw0rd!x", "role": "REVIEWER"}


def test_admin_can_create_and_list_users(client, admin):
    h = auth_header(client, "admin@example.com")
    r = client.post("/api/v1/users", json=NEW, headers=h)
    assert r.status_code == 201 and r.json()["role"] == "REVIEWER"
    assert {u["email"] for u in client.get("/api/v1/users", headers=h).json()} == {"admin@example.com", "rev@example.com"}


@pytest.mark.parametrize("role", ["OPERATOR", "REVIEWER", "COMPANY", "APPLICANT"])
def test_non_admin_roles_get_403(client, db_session, role):
    make_user(db_session, "x@example.com", role)
    h = auth_header(client, "x@example.com")
    for call in (lambda: client.get("/api/v1/users", headers=h), lambda: client.post("/api/v1/users", json=NEW, headers=h)):
        r = call()
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN"


def test_users_endpoint_needs_login(client):
    assert client.get("/api/v1/users").status_code == 401


def test_created_user_can_login(client, admin):
    client.post("/api/v1/users", json=NEW, headers=auth_header(client, "admin@example.com"))
    assert auth_header(client, "rev@example.com")


def test_duplicate_user_is_409_and_unknown_org_is_400(client, admin):
    h = auth_header(client, "admin@example.com")
    client.post("/api/v1/users", json=NEW, headers=h)
    assert client.post("/api/v1/users", json=NEW, headers=h).status_code == 409
    assert client.post("/api/v1/users", json={**NEW, "email": "z@example.com", "org_id": "nope"}, headers=h).status_code == 400


def test_change_role_and_deactivate(client, admin, db_session):
    target = make_user(db_session, "op@example.com", "OPERATOR")
    h = auth_header(client, "admin@example.com")
    r = client.patch(f"/api/v1/users/{target.user_id}", json={"role": "REVIEWER"}, headers=h)
    assert r.status_code == 200 and r.json()["role"] == "REVIEWER"
    r = client.patch(f"/api/v1/users/{target.user_id}", json={"is_active": False}, headers=h)
    assert r.json()["is_active"] is False
    ev = db_session.query(AuditEvent).filter_by(action="USER_UPDATE").all()
    assert len(ev) == 2 and ev[0].before_json["role"] == "OPERATOR"


def test_admin_cannot_demote_or_deactivate_self(client, admin):
    h = auth_header(client, "admin@example.com")
    assert client.patch(f"/api/v1/users/{admin.user_id}", json={"role": "OPERATOR"}, headers=h).status_code == 409
    assert client.patch(f"/api/v1/users/{admin.user_id}", json={"is_active": False}, headers=h).status_code == 409


def test_patch_unknown_user_is_404(client, admin):
    r = client.patch("/api/v1/users/does-not-exist", json={"is_active": False}, headers=auth_header(client, "admin@example.com"))
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"


def test_invalid_role_value_is_400(client, admin):
    r = client.post("/api/v1/users", json={**NEW, "role": "KING"}, headers=auth_header(client, "admin@example.com"))
    assert r.status_code == 400 and r.json()["error"]["details"]
