from app.models import AuditEvent, Organization, User
from tests.conftest import auth_header, login, make_user

REG_COMPANY = {"email": "Boss@Acme.com", "full_name": "Ann Boss", "password": "Passw0rd!x", "role": "COMPANY", "organization_name": "Acme SARL"}
REG_APPLICANT = {"email": "jean@example.com", "full_name": "Jean Dupont", "password": "Passw0rd!x", "role": "APPLICANT"}


# ---------- register ----------
def test_company_registration_creates_org_and_user(client, db_session, mailer):
    r = client.post("/api/v1/auth/register", json=REG_COMPANY)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["role"] == "COMPANY" and body["email"] == "boss@acme.com" and body["org_id"]
    assert "password" not in str(body) and "hash" not in str(body)
    assert db_session.query(Organization).filter_by(name="Acme SARL").count() == 1
    assert mailer.sent and mailer.sent[0][0] == "boss@acme.com"
    assert db_session.query(AuditEvent).filter_by(action="REGISTER").count() == 1


def test_applicant_registration_needs_no_company(client):
    assert client.post("/api/v1/auth/register", json=REG_APPLICANT).status_code == 201


def test_company_registration_requires_organization_name(client):
    bad = {k: v for k, v in REG_COMPANY.items() if k != "organization_name"}
    r = client.post("/api/v1/auth/register", json=bad)
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_cannot_self_register_as_admin(client):
    r = client.post("/api/v1/auth/register", json={**REG_APPLICANT, "role": "ADMIN"})
    assert r.status_code == 400


def test_duplicate_email_is_409(client):
    assert client.post("/api/v1/auth/register", json=REG_APPLICANT).status_code == 201
    r = client.post("/api/v1/auth/register", json={**REG_APPLICANT, "email": "JEAN@example.com"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "CONFLICT"


def test_duplicate_company_name_is_409(client):
    assert client.post("/api/v1/auth/register", json=REG_COMPANY).status_code == 201
    r = client.post("/api/v1/auth/register", json={**REG_COMPANY, "email": "other@acme.com"})
    assert r.status_code == 409


def test_short_password_and_bad_email_are_400(client):
    assert client.post("/api/v1/auth/register", json={**REG_APPLICANT, "password": "short"}).status_code == 400
    assert client.post("/api/v1/auth/register", json={**REG_APPLICANT, "email": "not-an-email"}).status_code == 400


def test_registration_survives_mail_failure(client, mailer):
    mailer.send = lambda *a, **k: False
    assert client.post("/api/v1/auth/register", json=REG_APPLICANT).status_code == 201


# ---------- login ----------
def test_login_success_returns_token_and_user(client, admin):
    r = login(client, "admin@example.com")
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 1800
    assert body["user"]["role"] == "ADMIN" and "password_hash" not in body["user"]
    assert admin.last_login_at is not None


def test_login_email_is_case_insensitive(client, admin):
    assert login(client, "ADMIN@Example.com").status_code == 200


def test_wrong_password_and_unknown_email_give_same_answer(client, admin):
    a = login(client, "admin@example.com", "wrong-password")
    b = login(client, "nobody@example.com", "whatever123")
    assert a.status_code == b.status_code == 401
    assert a.json()["error"]["message"] == b.json()["error"]["message"]


def test_account_locks_after_repeated_failures(client, admin, db_session):
    for _ in range(3):                                   # MAX_FAILED_LOGINS=3 in tests
        assert login(client, "admin@example.com", "bad-password").status_code == 401
    r = login(client, "admin@example.com")               # even the right password is refused while locked
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"
    assert "retry-after" in r.headers
    actions = {e.action for e in db_session.query(AuditEvent)}
    assert {"LOGIN_FAILED", "ACCOUNT_LOCKED", "LOGIN_BLOCKED"} <= actions


def test_lock_expires(client, admin, db_session):
    from datetime import timedelta
    from app.database.base import utcnow
    for _ in range(3):
        login(client, "admin@example.com", "bad-password")
    db_session.get(User, admin.user_id).locked_until = utcnow() - timedelta(seconds=1)
    db_session.commit()
    assert login(client, "admin@example.com").status_code == 200


def test_inactive_user_cannot_login(client, db_session):
    make_user(db_session, "gone@example.com", "OPERATOR", active=0)
    assert login(client, "gone@example.com").status_code == 401


def test_login_audit_does_not_contain_password(client, admin, db_session):
    login(client, "admin@example.com", "SuperSecretPw1")
    for e in db_session.query(AuditEvent):
        assert "SuperSecretPw1" not in f"{e.before_json}{e.after_json}{e.action}"


# ---------- me / bearer ----------
def test_me_requires_token(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED"
    assert r.headers.get("www-authenticate") == "Bearer"


def test_me_with_token(client, admin):
    r = client.get("/api/v1/auth/me", headers=auth_header(client, "admin@example.com"))
    assert r.status_code == 200 and r.json()["email"] == "admin@example.com"


def test_bad_token_is_401(client):
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


def test_deactivated_user_token_stops_working(client, admin, db_session):
    make_user(db_session, "op@example.com", "OPERATOR")
    h = auth_header(client, "op@example.com")
    assert client.get("/api/v1/auth/me", headers=h).status_code == 200
    db_session.query(User).filter_by(email="op@example.com").one().is_active = 0
    db_session.commit()
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401


def test_request_id_header_and_error_body(client):
    r = client.get("/api/v1/auth/me")
    assert r.headers["x-request-id"] == r.json()["error"]["request_id"]
