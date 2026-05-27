from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["embedding_configuration_ready"] is False
    assert payload["llm_configuration_ready"] is False
    assert payload["model_configuration_ready"] is False
