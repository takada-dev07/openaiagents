from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_workflow_run_creates_log() -> None:
    client = TestClient(app)

    payload = {
        "workflow": {
            "nodes": [
                {"id": "outline", "tool": "outline", "params": {"task": {"$ref": "input.task"}}, "retry": 0},
                {
                    "id": "image",
                    "tool": "generate_image",
                    "params": {"prompt": {"$ref": "input.task"}, "size": "256x256", "transparent": False},
                    "retry": 0,
                },
                {
                    "id": "pptx",
                    "tool": "render_pptx",
                    "params": {
                        "title": {"$ref": "results.outline.title"},
                        "slides": {"$ref": "results.outline.slides"},
                        "image_path": {"$ref": "results.image.image_path"},
                    },
                    "retry": 0,
                },
            ],
            "edges": [
                {"from": "outline", "to": "image"},
                {"from": "image", "to": "pptx"},
            ],
        },
        "input": {"task": "ワークフローのテスト"},
    }

    r = client.post("/workflow/run", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    log_path = Path(data["log_path"])
    assert log_path.exists()

    log = json.loads(log_path.read_text(encoding="utf-8"))
    assert log["order"] == ["outline", "image", "pptx"]
    assert "results" in log
    assert "pptx" in log["results"]


