from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class OpenAIImageResult:
    png_bytes: bytes
    model: str
    revised_prompt: str | None = None


class OpenAIClient:
    """
    Minimal HTTP client wrapper so we can swap implementations later.
    - If api_key is empty, caller should avoid calling and fallback to dummy behavior.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def generate_image(
        self,
        *,
        prompt: str,
        size: str = "1024x1024",
        transparent: bool = False,
        model: str = "gpt-image-1",
        timeout_sec: float = 60.0,
    ) -> OpenAIImageResult:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "response_format": "b64_json",
        }
        if transparent:
            # API supports background control for some models; keep best-effort.
            payload["background"] = "transparent"

        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            r = await client.post(f"{self.base_url}/images/generations", headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        # Expect: {"data":[{"b64_json":"...","revised_prompt":"..."}]}
        item = (data.get("data") or [{}])[0]
        b64 = item.get("b64_json")
        if not b64:
            raise RuntimeError(f"OpenAI image response missing b64_json: {data}")
        png = base64.b64decode(b64)
        return OpenAIImageResult(
            png_bytes=png,
            model=model,
            revised_prompt=item.get("revised_prompt"),
        )


