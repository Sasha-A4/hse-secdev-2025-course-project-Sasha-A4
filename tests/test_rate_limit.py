from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_rate_limit_returns_429_when_exceeded():
    hit_429 = False
    for _ in range(20):
        r = client.get("/features")
        if r.status_code == 429:
            hit_429 = True
            body = r.json()
            assert body["status"] == 429
            assert body["title"] == "Too Many Requests"
            assert body["type"].endswith("/problems/rate_limited")
            assert "correlation_id" in body
            break

    assert hit_429, "Expected at least one 429 when exceeding 10 RPS limit"
