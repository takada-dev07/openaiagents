from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings, new_trace_id
from app.core.logging import get_logger
from app.models.schemas import PptxSlideSpec
from app.services.image_service import ImageService
from app.services.pptx_service import PptxService


@dataclass(frozen=True)
class AgentRunResult:
    trace_id: str
    result: str
    artifacts: list[str]


class AgentRunner:
    """
    Minimal agent runner that *mimics* tool-calling:
    - Simple router based on task text
    - Executes a sequence of tool functions
    - Writes a trace JSON to artifacts/traces/<trace_id>.json
    """

    def __init__(self, *, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.log = get_logger(__name__)
        self.image_service = ImageService(settings=self.settings)
        self.pptx_service = PptxService(settings=self.settings)

        # Expose tools to workflow engine
        self.tools = {
            "outline": self.tool_outline,
            "generate_image": self.tool_generate_image,
            "render_pptx": self.tool_render_pptx,
            "explain_pptx": self.tool_explain_pptx,
            "passthrough": self.tool_passthrough,
        }

    async def run(self, *, task: str, context: dict[str, Any]) -> AgentRunResult:
        trace_id = new_trace_id()
        trace_path = self.settings.artifact_dir / "traces" / f"{trace_id}.json"

        artifacts: list[str] = [str(trace_path)]
        steps: list[dict[str, Any]] = []

        def record(tool: str, status: str, start_ts: float, **fields: Any) -> None:
            steps.append(
                {"tool": tool, "status": status, "start_ts": start_ts, "end_ts": time.time(), **fields}
            )

        result_text = ""
        router = self._route(task)
        self.log.info("Agent route selected", extra={"trace_id": trace_id, "route": router})

        try:
            if router == "pptx_flow":
                start = time.time()
                outline = await self.tool_outline(task=task, context=context)
                record("outline", "completed", start, output=outline)

                start = time.time()
                img = await self.tool_generate_image(prompt=task, size="1024x1024", transparent=False, context=context)
                artifacts.append(img["image_path"])
                record("generate_image", "completed", start, output=img)

                start = time.time()
                deck = await self.tool_render_pptx(
                    title=outline["title"],
                    slides=outline["slides"],
                    image_path=img["image_path"],
                    context=context,
                )
                artifacts.extend(deck.get("artifacts", []))
                record("render_pptx", "completed", start, output=deck)

                start = time.time()
                explained = await self.tool_explain_pptx(pptx_path=deck["pptx_path"], context=context)
                artifacts.extend(explained.get("images", []))
                record("explain_pptx", "completed", start, output={"slide_count": len(explained["slides"])})

                result_text = (
                    f"PPTXを生成しました: {deck['pptx_path']}\n"
                    f"スライド説明を生成しました（{len(explained['slides'])}枚）"
                )
            else:
                start = time.time()
                echo = {"message": "まだ最小ルータです。taskをそのまま返します。", "task": task, "context": context}
                record("passthrough", "completed", start, output=echo)
                result_text = json.dumps(echo, ensure_ascii=False)

            trace_path.write_text(
                json.dumps(
                    {"trace_id": trace_id, "task": task, "context": context, "steps": steps, "artifacts": artifacts},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as e:
            steps.append({"tool": "agent", "status": "failed", "error": str(e), "ts": time.time()})
            trace_path.write_text(
                json.dumps(
                    {"trace_id": trace_id, "task": task, "context": context, "steps": steps, "artifacts": artifacts},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            raise

        return AgentRunResult(trace_id=trace_id, result=result_text, artifacts=artifacts)

    def _route(self, task: str) -> str:
        t = task.lower()
        if any(k in t for k in ["ppt", "pptx", "パワポ", "powerpoint", "資料", "スライド"]):
            return "pptx_flow"
        return "passthrough"

    # -------- tools (must accept context=...) --------

    async def tool_outline(self, *, task: str, context: dict[str, Any]) -> dict[str, Any]:
        # Minimal, rule-based outline.
        title = context.get("title") or "学習用デモ資料"
        slides = [
            PptxSlideSpec(
                heading="ゴール",
                bullets=[
                    "tool calling / 多段処理 / 失敗時の扱いを学ぶ",
                    "画像生成APIの雛形を差し替え可能にする",
                    "PPTX生成→画像化→説明までの土台を作る",
                ],
            ),
            PptxSlideSpec(
                heading="入力タスク",
                bullets=[task],
            ),
        ]
        return {"title": title, "slides": slides}

    async def tool_generate_image(
        self, *, prompt: str, size: str = "1024x1024", transparent: bool = False, context: dict[str, Any]
    ) -> dict[str, Any]:
        res = await self.image_service.generate(prompt=prompt, size=size, transparent=transparent)
        return {"image_path": res.image_path, "artifact_id": res.artifact_id, "trace_id": res.trace_id}

    async def tool_render_pptx(
        self,
        *,
        title: str,
        slides: list[PptxSlideSpec],
        image_path: str | None = None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        # Attach the same image to slides that don't already have one (minimal demo).
        patched: list[PptxSlideSpec] = []
        for s in slides:
            if s.image_path or not image_path:
                patched.append(s)
            else:
                patched.append(PptxSlideSpec(heading=s.heading, bullets=s.bullets, image_path=image_path))

        res = await self.pptx_service.render_deck(title=title, slides=patched)
        return {"pptx_path": res.pptx_path, "trace_id": res.trace_id, "artifacts": res.artifacts}

    async def tool_explain_pptx(self, *, pptx_path: str, context: dict[str, Any]) -> dict[str, Any]:
        res = await self.pptx_service.explain_deck(pptx_path=pptx_path)
        return {
            "trace_id": res.trace_id,
            "slides": [s.model_dump() for s in res.slides],
            "images": res.images,
            "warnings": res.warnings,
        }

    def tool_passthrough(self, *, value: Any = None, context: dict[str, Any]) -> dict[str, Any]:
        return {"value": value, "context": context}


