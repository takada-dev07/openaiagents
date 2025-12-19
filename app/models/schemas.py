from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class AgentRunRequest(BaseModel):
    task: str = Field(..., description="ユーザーのタスク指示（日本語想定）")
    context: dict[str, Any] = Field(default_factory=dict, description="追加コンテキスト")


class AgentRunResponse(BaseModel):
    result: str
    trace_id: str
    artifacts: list[str] = Field(default_factory=list)


class ImageGenerateRequest(BaseModel):
    prompt: str
    size: str = Field(default="1024x1024", description="例: 1024x1024")
    transparent: bool = False


class ImageGenerateResponse(BaseModel):
    image_path: str
    artifact_id: str
    trace_id: str


class PptxSlideSpec(BaseModel):
    heading: str
    bullets: list[str] = Field(default_factory=list)
    image_path: str | None = None


class PptxRenderRequest(BaseModel):
    title: str
    slides: list[PptxSlideSpec] = Field(default_factory=list)


class PptxRenderResponse(BaseModel):
    pptx_path: str
    trace_id: str
    artifacts: list[str] = Field(default_factory=list)


class PptxExplainRequest(BaseModel):
    pptx_path: str


class ExplainedSlide(BaseModel):
    slide: int
    text: str
    notes: str
    explain: str


class PptxExplainResponse(BaseModel):
    slides: list[ExplainedSlide]
    images: list[str]
    trace_id: str
    warnings: list[str] = Field(default_factory=list)


class WorkflowEdge(BaseModel):
    from_: str = Field(..., alias="from")
    to: str


class WorkflowNode(BaseModel):
    id: str
    tool: str
    params: dict[str, Any] = Field(default_factory=dict)
    retry: int = 0
    timeout_sec: float | None = None


class WorkflowSpec(BaseModel):
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge] = Field(default_factory=list)


class WorkflowRunRequest(BaseModel):
    workflow: WorkflowSpec
    input: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunResponse(BaseModel):
    trace_id: str
    results: dict[str, Any]
    log_path: str


