import os

# Settings for tests: set BEFORE the app is imported. Fast password hashing, no real e-mail.
os.environ.setdefault("PASSWORD_SCRYPT_N", "1024")
os.environ.setdefault("EMAIL_BACKEND", "console")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret")
os.environ.setdefault("MAX_FAILED_LOGINS", "3")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database.base import Base
from app.database.connection import get_db
from app.main import app
from app.models import User
from app.services.email import get_email_service


class FakeMailer:
    def __init__(self):
        self.sent = []

    def send(self, to, subject, body):
        self.sent.append((to, subject, body))
        return True


@pytest.fixture()
def db_session():
    """A fresh in-memory SQLite database per test (fast unit tests; MySQL-only rules are tested in test_mysql_integration.py)."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def mailer():
    return FakeMailer()


@pytest.fixture()
def client(db_session, mailer):
    def override_db():
        yield db_session
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_email_service] = lambda: mailer
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(db, email, role, password="Passw0rd!x", active=1, org_id=None):
    u = User(email=email, full_name=email.split("@")[0].title(), password_hash=hash_password(password), role=role, is_active=active, org_id=org_id)
    db.add(u)
    db.commit()
    return u


@pytest.fixture()
def admin(db_session):
    return make_user(db_session, "admin@example.com", "ADMIN")


def login(client, email, password="Passw0rd!x"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def auth_header(client, email, password="Passw0rd!x"):
    r = login(client, email, password)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
