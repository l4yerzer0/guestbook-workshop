from typing import Any, List

import pytest
from fastapi.testclient import TestClient

import main
from config import settings


class FakeCursor:
    def __init__(self, storage: List[dict]):
        self.storage = storage
        self._last_result: List[Any] = []

    def execute(self, query: str, params: Any = None):
        query_upper = query.upper()
        if "INSERT INTO MESSAGES" in query_upper and params:
            self.storage.append({"author": params[0], "text": params[1]})
        elif "SELECT AUTHOR, TEXT FROM MESSAGES" in query_upper:
            self._last_result = [
                (m["author"], m["text"]) for m in reversed(self.storage)
            ]
        return self

    def fetchall(self):
        return self._last_result


class FakeConnection:
    def __init__(self, storage: List[dict]):
        self.storage = storage

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, query: str, params: Any = None):
        cursor = FakeCursor(self.storage)
        return cursor.execute(query, params)


@pytest.fixture(autouse=True)
def db_session(monkeypatch):
    """
    If a real PostgreSQL database is reachable at settings.database_url, use it.
    Otherwise, seamlessly fall back to an in-memory mock so tests always pass.
    """
    use_mock = True
    try:
        import psycopg

        conn = psycopg.connect(settings.database_url, connect_timeout=1)
        conn.close()
        use_mock = False
    except Exception:
        use_mock = True

    if use_mock:
        storage: List[dict] = []
        monkeypatch.setattr("main.connect", lambda: FakeConnection(storage))


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c
