from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_not_found_item():
    r = client.get("/items/999")
    assert r.status_code == 404
    body = r.json()
    assert body["status"] == 404
    assert body["title"] == "Not Found"
    assert body["type"].endswith("/problems/not_found")
    assert "correlation_id" in body


def test_validation_error():
    r = client.post("/items", params={"name": ""})
    assert r.status_code == 422
    body = r.json()
    assert body["status"] == 422
    assert body["title"] == "Validation Error"
    assert body["type"].endswith("/problems/validation_error")
    assert "correlation_id" in body
