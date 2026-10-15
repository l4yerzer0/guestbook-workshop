from config import settings


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": settings.greeting}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
