"""Integration tests against a REAL MySQL / MariaDB server. They are skipped unless you opt in.

To run them, create an EMPTY test database and give your DB user rights on it, then set the variable:
    CREATE DATABASE idp_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    $env:IDP_TEST_DATABASE = "idp_test"        # PowerShell
    .\\.venv\\Scripts\\python.exe -m pytest tests/test_mysql_integration.py -v
The connection uses DB_HOST / DB_PORT / DB_USER / DB_PASSWORD from backend/.env; only the database name differs.
The test database is emptied again at the end. NEVER point it at your real idp_db.
"""
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.database.connection import get_db
from app.main import app
from app.models import AuditEvent, Base, User
from app.services.email import get_email_service
from tests.conftest import FakeMailer, auth_header

TEST_DB = os.environ.get("IDP_TEST_DATABASE")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="set IDP_TEST_DATABASE to run the MySQL integration tests")

BACKEND = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def engine():
    assert TEST_DB != get_settings().db_name, "refusing to run on the real database"
    url = get_settings().sqlalchemy_url.set(database=TEST_DB)
    eng = create_engine(url)
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.attributes["connection_url"] = url
    with eng.connect() as c:
        left = inspect(c).get_table_names()
    assert not left, f"{TEST_DB} is not empty ({left}); use an empty test database"
    command.upgrade(cfg, "head")
    yield eng
    command.downgrade(cfg, "base")
    with eng.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS alembic_version"))
    eng.dispose()


@pytest.fixture()
def session(engine):
    s = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield s
    s.rollback()
    s.close()


def test_migration_creates_16_tables_2_triggers_6_settings(engine):
    with engine.connect() as c:
        tables = set(inspect(c).get_table_names()) - {"alembic_version"}
        triggers = c.execute(text("SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema = DATABASE()")).scalar()
        settings = c.execute(text("SELECT COUNT(*) FROM system_settings")).scalar()
    assert len(tables) == 16 and triggers == 2 and settings == 6


def test_models_match_database_columns(engine):
    insp = inspect(engine)
    for name, table in Base.metadata.tables.items():
        db_cols = {c["name"] for c in insp.get_columns(name)}
        assert {c.name for c in table.columns} == db_cols, f"model and database differ for {name}"


def test_check_constraint_refuses_unknown_role(session):
    session.add(User(email="k@example.com", full_name="K", password_hash="x", role="KING"))
    with pytest.raises((IntegrityError, DBAPIError)):
        session.commit()


def test_audit_events_are_append_only(session):
    ev = AuditEvent(action="TEST")
    session.add(ev)
    session.commit()
    with pytest.raises(DBAPIError) as e:
        session.execute(text("UPDATE audit_events SET action = 'x' WHERE event_id = :i"), {"i": ev.event_id})
    assert "append-only" in str(e.value)
    session.rollback()
    with pytest.raises(DBAPIError) as e:
        session.execute(text("DELETE FROM audit_events WHERE event_id = :i"), {"i": ev.event_id})
    assert "append-only" in str(e.value)
    session.rollback()


def test_register_login_me_on_real_database(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    sess = Session()

    def override():
        yield sess
    app.dependency_overrides[get_db] = override
    app.dependency_overrides[get_email_service] = lambda: FakeMailer()
    try:
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.post("/api/v1/auth/register", json={"email": "real@example.com", "full_name": "Real User", "password": "Passw0rd!x",
                                                   "role": "COMPANY", "organization_name": "Real Co"})
        assert r.status_code == 201, r.text
        assert c.post("/api/v1/auth/register", json={"email": "real@example.com", "full_name": "Again", "password": "Passw0rd!x",
                                                      "role": "APPLICANT"}).status_code == 409
        me = c.get("/api/v1/auth/me", headers=auth_header(c, "real@example.com"))
        assert me.status_code == 200 and me.json()["role"] == "COMPANY" and me.json()["org_id"]
        assert sess.query(AuditEvent).filter(AuditEvent.action.in_(["REGISTER", "LOGIN"])).count() == 2
    finally:
        app.dependency_overrides.clear()
        sess.close()
