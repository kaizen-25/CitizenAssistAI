from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_scheme_counts_and_llm_state(monkeypatch):
    monkeypatch.setattr("app.api.health.is_available", lambda: False)

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["llm_available"] is False
    assert body["schemes_loaded"] == sum(body["verified_by_category"].values())


def test_cors_allows_vite_dev_server():
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
