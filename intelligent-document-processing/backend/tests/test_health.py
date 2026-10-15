from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_running_status():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health_endpoint_is_healthy():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "idp-backend"


def test_health_db_returns_503_when_database_is_down(monkeypatch):
    monkeypatch.setattr("app.api.health.check_database", lambda: False)
    response = client.get("/api/v1/health/db")
    assert response.status_code == 503
    assert response.json()["database"] == "unreachable"


def test_health_db_returns_200_when_database_is_up(monkeypatch):
    monkeypatch.setattr("app.api.health.check_database", lambda: True)
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"
