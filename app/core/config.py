from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_organization_id: str
    openai_project_id: str
    openai_image_model: str
    artifact_dir: Path
    log_level: str


def new_trace_id() -> str:
    return uuid.uuid4().hex


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Load .env if present (devcontainer/local). .env.example is intentionally not used.
    load_dotenv(override=False)

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_organization_id = os.getenv("OPENAI_ORGANIZATION_ID", "").strip()
    openai_project_id = os.getenv("OPENAI_PROJECT_ID", "").strip()
    openai_image_model = (
        os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1").strip() or "gpt-image-1"
    )
    artifact_dir = Path(os.getenv("ARTIFACT_DIR", "artifacts")).resolve()
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "traces").mkdir(parents=True, exist_ok=True)
    (artifact_dir / "images").mkdir(parents=True, exist_ok=True)
    (artifact_dir / "slides").mkdir(parents=True, exist_ok=True)
    (artifact_dir / "workflows").mkdir(parents=True, exist_ok=True)

    return Settings(
        openai_api_key=openai_api_key,
        openai_organization_id=openai_organization_id,
        openai_project_id=openai_project_id,
        openai_image_model=openai_image_model,
        artifact_dir=artifact_dir,
        log_level=log_level,
    )
