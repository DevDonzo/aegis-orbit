from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_live_satellites_endpoint() -> None:
    # Without refresh (default) – should return records and source information
    response = client.get("/satellites/live")
    assert response.status_code == 200
    payload = response.json()
    assert "source" in payload and isinstance(payload["source"], dict)
    assert "records" in payload and isinstance(payload["records"], list)
    # At least one record should be present (sample data ensures this)
    assert len(payload["records"]) > 0
    first = payload["records"][0]
    # Verify essential fields exist and are correctly typed
    assert "name" in first and isinstance(first["name"], str)
    assert "norad_id" in first and isinstance(first["norad_id"], str)
    assert "line1" in first and isinstance(first["line1"], str)
    assert "line2" in first and isinstance(first["line2"], str)
    # Source mode should be one of the expected values
    assert payload["source"].get("mode") in {"live", "cache", "sample"}
