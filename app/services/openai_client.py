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


class OpenAIRequestError(RuntimeError):
    def __init__(self, *, status_code: int, body: str) -> None:
        super().__init__(f"OpenAI request failed: status={status_code} body={body}")
        self.status_code = status_code
        self.body = body


class OpenAIClient:
    """
    Minimal HTTP client wrapper so we can swap implementations later.
    - If api_key is empty, caller should avoid calling and fallback to dummy behavior.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        *,
        organization_id: str = "",
        project_id: str = "",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.organization_id = organization_id.strip()
        self.project_id = project_id.strip()

    async def generate_image(
        self, *, payload: dict[str, Any], timeout_sec: float = 60.0
    ) -> OpenAIImageResult:
        headers: dict[str, str] = {"Authorization": f"Bearer {self.api_key}"}
        if self.organization_id:
            headers["OpenAI-Organization"] = self.organization_id
        if self.project_id:
            headers["OpenAI-Project"] = self.project_id
        req_payload: dict[str, Any] = dict(payload)
        # Local-only keys should never be sent to OpenAI.
        req_payload.pop("transparent", None)

        if "prompt" not in req_payload or not req_payload["prompt"]:
            raise ValueError("payload.prompt is required")
        if "size" not in req_payload or not req_payload["size"]:
            raise ValueError("payload.size is required")

        # Some models/endpoints reject response_format; only default it for DALL·E models.
        model = str(req_payload.get("model") or "")
        if model.startswith("dall-e-"):
            req_payload.setdefault("response_format", "b64_json")

        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            r = await client.post(
                f"{self.base_url}/images/generations", headers=headers, json=req_payload
            )
            # Best-effort compatibility retry: if an unknown parameter is rejected, retry once without it.
            if r.status_code == 400:
                try:
                    err = (
                        (r.json().get("error") or {})
                        if r.headers.get("content-type", "").startswith(
                            "application/json"
                        )
                        else {}
                    )
                except Exception:
                    err = {}
                param = err.get("param")
                code = err.get("code")
                if code == "unknown_parameter" and param in {
                    "background",
                    "response_format",
                }:
                    retry_payload = dict(req_payload)
                    retry_payload.pop(param, None)
                    r = await client.post(
                        f"{self.base_url}/images/generations",
                        headers=headers,
                        json=retry_payload,
                    )
            if r.status_code >= 400:
                # Surface the OpenAI error body to help debugging (returned as 502 upstream).
                raise OpenAIRequestError(status_code=r.status_code, body=r.text)
            data = r.json()

        # Expect: {"data":[{"b64_json":"...","revised_prompt":"..."}]}
        item = (data.get("data") or [{}])[0]
        b64 = item.get("b64_json")
        if not b64:
            raise RuntimeError(f"OpenAI image response missing b64_json: {data}")
        png = base64.b64decode(b64)
        actual_model = str(req_payload.get("model") or "default")
        return OpenAIImageResult(
            png_bytes=png,
            model=actual_model,
            revised_prompt=item.get("revised_prompt"),
        )
