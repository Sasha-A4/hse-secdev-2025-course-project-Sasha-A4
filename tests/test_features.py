from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_feature():
    r = client.post(
        "/features",
        json={
            "title": "Search",
            "description": "Add search bar",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == 1
    assert data["title"] == "Search"
    assert data["votes"] == 0


def test_get_feature():
    # Фича уже создана в предыдущем тесте
    r = client.get("/features/1")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == 1
    assert data["title"] == "Search"


def test_vote_feature():
    r = client.post("/features/1/vote", json={"value": 1})
    assert r.status_code == 200
    data = r.json()
    assert data["votes"] == 1


def test_create_second_feature_and_vote():
    r = client.post(
        "/features",
        json={
            "title": "Notifications",
            "description": "Push alerts",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == 2

    # Голосуем дважды
    client.post("/features/2/vote", json={"value": 1})
    client.post("/features/2/vote", json={"value": 1})

    r2 = client.get("/features/2")
    assert r2.status_code == 200
    assert r2.json()["votes"] == 2


def test_top_features():
    r = client.get("/features/top?limit=1")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1
    # В топе должна быть Notifications (2 голоса), а не Search (1 голос)
    assert data[0]["title"] == "Notifications"
    assert data[0]["votes"] == 2


def test_vote_validation_error():
    # Используем отдельный клиент для избежания rate limiting
    test_client = TestClient(app)
    r = test_client.post("/features/2/vote", json={"value": 5})
    assert r.status_code == 422
    body = r.json()
    assert body["status"] == 422
    assert body["title"] == "Validation Error"
    assert body["type"].endswith("/problems/validation_error")
    assert "correlation_id" in body


def test_get_feature_not_found_problem():
    # Используем отдельный клиент для избежания rate limiting
    test_client = TestClient(app)
    r = test_client.get("/features/9999")
    assert r.status_code == 404
    body = r.json()
    assert body["status"] == 404
    assert body["title"] == "Not Found"
    assert body["type"].endswith("/problems/not_found")
    assert "correlation_id" in body
