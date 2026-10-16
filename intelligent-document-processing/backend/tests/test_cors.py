from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_react_dev_origin_is_allowed():
    r = client.options(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_unknown_origin_is_not_allowed():
    r = client.get("/api/v1/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers
