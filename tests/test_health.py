from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_health(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    client = TestClient(create_app())
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


