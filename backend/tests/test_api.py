from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_response_shape() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "source_status" in body


def test_satellites_response_shape() -> None:
    response = client.get("/satellites")
    assert response.status_code == 200
    satellites = response.json()
    assert len(satellites) > 0
    first = satellites[0]
    assert first["name"]
    assert isinstance(first["lat"], float)
    assert first["source_type"] in {"live", "cache", "sample"}


def test_collisions_response_shape() -> None:
    response = client.get("/collisions", params={"limit": 5})
    assert response.status_code == 200
    collisions = response.json()
    assert len(collisions) > 0
    first = collisions[0]
    assert first["min_distance_km"] >= 0
    assert first["relative_speed_km_s"] >= 0
    assert first["risk"] in {"danger", "warning", "safe"}
    assert first["data_source"] in {"live", "cache", "sample"}


def test_top_risks_and_history() -> None:
    top_response = client.get("/top-risks", params={"limit": 3})
    assert top_response.status_code == 200
    top = top_response.json()
    assert len(top) > 0
    history_response = client.get("/history", params={"limit": 10})
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history["events"]) > 0


def test_predict_optional_ml_safe_without_model() -> None:
    response = client.get("/predict", params={"limit": 3})
    assert response.status_code == 200
    predictions = response.json()
    assert len(predictions) > 0
    for item in predictions:
        assert item["predicted_min_distance_km"] >= 0
        assert item["predicted_risk"] in {"danger", "warning", "safe"}
        assert isinstance(item["ml_available"], bool)


def test_source_status_endpoint() -> None:
    response = client.get("/source-status")
    assert response.status_code == 200
    status = response.json()
    assert status["mode"] in {"live", "cache", "sample"}
