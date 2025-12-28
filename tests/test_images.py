from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_images_generate_accepts_extra_fields(monkeypatch) -> None:
    # Force dummy mode to avoid network calls.
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    client = TestClient(create_app())

    payload = {
        "prompt": "テスト画像",
        "size": "256x256",
        "transparent": False,
        # Known optional fields
        "model": "gpt-image-1",
        "quality": "high",
        # Unknown forward-compatible field (should not 422)
        "future_param": {"any": "thing"},
    }
    r = client.post("/images/generate", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "image_path" in data
    assert Path(data["image_path"]).exists()


