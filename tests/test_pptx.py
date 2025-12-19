from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_pptx_render_and_explain(tmp_path: Path) -> None:
    # Ensure artifacts go to temp for test isolation
    # (config reads env once; this test assumes default artifacts path is writable)
    client = TestClient(app)

    render_payload = {
        "title": "テスト資料",
        "slides": [
            {"heading": "見出し1", "bullets": ["項目A", "項目B"]},
            {"heading": "見出し2", "bullets": ["項目C"]},
        ],
    }
    r = client.post("/pptx/render", json=render_payload)
    assert r.status_code == 200, r.text
    data = r.json()
    pptx_path = Path(data["pptx_path"])
    assert pptx_path.exists()
    assert pptx_path.stat().st_size > 0

    r2 = client.post("/pptx/explain", json={"pptx_path": str(pptx_path)})
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert "slides" in d2
    assert len(d2["slides"]) >= 1

    # Image conversion depends on environment (LibreOffice/poppler). If images are present, they should exist.
    for p in d2.get("images", []):
        assert Path(p).exists()


