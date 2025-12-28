from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.agents.agent_runner import AgentRunner
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.models.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    HealthResponse,
    ImageGenerateRequest,
    ImageGenerateResponse,
    PptxExplainRequest,
    PptxExplainResponse,
    PptxRenderRequest,
    PptxRenderResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
)
from app.services.image_service import ImageService
from app.services.openai_client import OpenAIRequestError
from app.services.pptx_service import PptxService
from app.services.workflow_service import WorkflowService


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger(__name__)

    app = FastAPI(title="openaiagents", version="0.1.0")

    agent = AgentRunner(settings=settings)
    image_service = ImageService(settings=settings)
    pptx_service = PptxService(settings=settings)
    workflow_service = WorkflowService(settings=settings, tools=agent.tools)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.post("/agent/run", response_model=AgentRunResponse)
    async def agent_run(req: AgentRunRequest) -> AgentRunResponse:
        res = await agent.run(task=req.task, context=req.context)
        return AgentRunResponse(
            result=res.result, trace_id=res.trace_id, artifacts=res.artifacts
        )

    @app.post("/images/generate", response_model=ImageGenerateResponse)
    async def images_generate(req: ImageGenerateRequest) -> ImageGenerateResponse:
        try:
            res = await image_service.generate(
                prompt=req.prompt,
                size=req.size,
                transparent=req.transparent,
                params=req.model_dump(exclude_none=True),
            )
        except OpenAIRequestError as e:
            # Bubble up the OpenAI error body for debugging.
            raise HTTPException(
                status_code=502,
                detail={"openai_status": e.status_code, "openai_body": e.body},
            ) from e
        return ImageGenerateResponse(
            image_path=res.image_path,
            artifact_id=res.artifact_id,
            trace_id=res.trace_id,
        )

    @app.post("/pptx/render", response_model=PptxRenderResponse)
    async def pptx_render(req: PptxRenderRequest) -> PptxRenderResponse:
        res = await pptx_service.render_deck(title=req.title, slides=req.slides)
        return PptxRenderResponse(
            pptx_path=res.pptx_path, trace_id=res.trace_id, artifacts=res.artifacts
        )

    @app.post("/pptx/explain", response_model=PptxExplainResponse)
    async def pptx_explain(req: PptxExplainRequest) -> PptxExplainResponse:
        res = await pptx_service.explain_deck(pptx_path=req.pptx_path)
        return PptxExplainResponse(
            slides=res.slides,
            images=res.images,
            trace_id=res.trace_id,
            warnings=res.warnings,
        )

    @app.post("/workflow/run", response_model=WorkflowRunResponse)
    async def workflow_run(req: WorkflowRunRequest) -> WorkflowRunResponse:
        res = await workflow_service.run(workflow=req.workflow, input_data=req.input)
        return WorkflowRunResponse(
            trace_id=res.trace_id, results=res.results, log_path=res.log_path
        )

    log.info("App created", extra={"artifact_dir": str(settings.artifact_dir)})
    return app


app = create_app()
