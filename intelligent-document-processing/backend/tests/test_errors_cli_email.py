import logging

from fastapi.testclient import TestClient

from app.cli import create_admin
from app.core.config import Settings
from app.main import app
from app.models import User
from app.services.email import EmailService


def test_unknown_path_uses_error_format(client):
    r = client.get("/api/v1/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"


def test_unexpected_error_hides_details():
    @app.get("/__boom", include_in_schema=False)
    def boom():
        raise RuntimeError("secret path C:\\private\\file")
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/__boom")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "private" not in r.text and "Traceback" not in r.text


def test_console_email_logs_without_body(caplog):
    caplog.set_level(logging.INFO, logger="idp.email")
    ok = EmailService(Settings(email_backend="console")).send("a@b.co", "Hello", "SECRET BODY")
    assert ok and "a@b.co" in caplog.text and "SECRET BODY" not in caplog.text


def test_smtp_without_settings_returns_false_and_does_not_raise(caplog):
    ok = EmailService(Settings(email_backend="smtp", smtp_login="", smtp_key="")).send("a@b.co", "Hi", "x")
    assert ok is False


def test_smtp_failure_never_logs_the_key(caplog, monkeypatch):
    import smtplib

    class Boom:
        def __init__(self, *a, **k):
            raise ConnectionRefusedError("no route")
    monkeypatch.setattr(smtplib, "SMTP", Boom)
    s = Settings(email_backend="smtp", smtp_login="login@x.com", smtp_key="TOPSECRETKEY", email_from="me@x.com")
    assert EmailService(s).send("a@b.co", "Hi", "x") is False
    assert "TOPSECRETKEY" not in caplog.text


def test_smtp_success_path_uses_starttls_and_login(monkeypatch):
    import smtplib
    calls = []

    class Fake:
        def __init__(self, host, port, timeout=None): calls.append(("connect", host, port))
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, context=None): calls.append(("starttls",))
        def login(self, user, key): calls.append(("login", user))
        def send_message(self, msg): calls.append(("send", msg["To"], msg["Subject"]))
    monkeypatch.setattr(smtplib, "SMTP", Fake)
    s = Settings(email_backend="smtp", smtp_login="login@x.com", smtp_key="k", email_from="me@x.com")
    assert EmailService(s).send("a@b.co", "Hi", "x") is True
    assert [c[0] for c in calls] == ["connect", "starttls", "login", "send"]
    assert calls[0][1:] == ("smtp-relay.brevo.com", 587)


def test_create_admin_cli(db_session, monkeypatch):
    import app.cli as cli
    monkeypatch.setattr(cli, "get_sessionmaker", lambda: (lambda: db_session))
    monkeypatch.setattr(db_session, "close", lambda: None)
    assert create_admin("Root@Example.com", "Root", password="Passw0rd!x") == 0
    assert db_session.query(User).filter_by(email="root@example.com", role="ADMIN").count() == 1
    assert create_admin("root@example.com", "Root", password="Passw0rd!x") == 1     # already exists
    assert create_admin("x@example.com", "X", password="short") == 1
