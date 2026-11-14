from config import settings


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": settings.greeting}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_success(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_failure(client, monkeypatch):
    def failing_connect(*args, **kwargs):
        raise ConnectionError("Cannot reach database")

    monkeypatch.setattr("main.connect", failing_connect)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "detail": "Database connection failed",
    }


def test_metrics(client):
    # Trigger a request to increment counters
    client.get("/")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text


def test_alerts_webhook(client):
    payload = {
        "version": "4",
        "groupKey": '{}:{alertname="HighRequestRate"}',
        "status": "firing",
        "receiver": "app-webhook",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HighRequestRate",
                    "severity": "warning",
                },
                "annotations": {
                    "summary": "High request rate detected",
                },
            }
        ],
    }
    response = client.post("/alerts/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"ok": True, "received": 1}


def test_messages_lifecycle(client):
    # Ensure empty or initial list is reachable
    response = client.get("/messages")
    assert response.status_code == 200

    # Add first message
    resp1 = client.post(
        "/messages", json={"author": "Alice", "text": "Первое сообщение"}
    )
    assert resp1.status_code == 200
    assert resp1.json() == {"ok": True}

    # Add second message
    resp2 = client.post("/messages", json={"author": "Bob", "text": "Второе сообщение"})
    assert resp2.status_code == 200
    assert resp2.json() == {"ok": True}

    # Verify order: newest first
    messages = client.get("/messages").json()
    assert len(messages) >= 2
    assert messages[0] == {"author": "Bob", "text": "Второе сообщение"}
    assert messages[1] == {"author": "Alice", "text": "Первое сообщение"}


def test_invalid_message_payload(client):
    # Missing required fields should return 422 Unprocessable Entity
    response = client.post("/messages", json={"author": "Nobody"})
    assert response.status_code == 422
