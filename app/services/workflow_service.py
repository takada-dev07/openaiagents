from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

import networkx as nx
from pydantic import BaseModel

from app.core.config import Settings, get_settings, new_trace_id
from app.core.logging import get_logger
from app.models.schemas import WorkflowSpec


ToolFn = Callable[..., Any]  # may be sync or async


@dataclass(frozen=True)
class WorkflowRunResult:
    trace_id: str
    results: dict[str, Any]
    log_path: str


class WorkflowService:
    def __init__(self, *, settings: Settings | None = None, tools: dict[str, ToolFn] | None = None) -> None:
        self.settings = settings or get_settings()
        self.tools = tools or {}
        self.log = get_logger(__name__)

    async def run(self, *, workflow: WorkflowSpec, input_data: dict[str, Any]) -> WorkflowRunResult:
        trace_id = new_trace_id()
        out_path = self.settings.artifact_dir / "workflows" / f"{trace_id}.json"

        graph = nx.DiGraph()
        for node in workflow.nodes:
            graph.add_node(node.id, node=node)
        for edge in workflow.edges:
            graph.add_edge(edge.from_, edge.to)

        order = list(nx.topological_sort(graph))
        results: dict[str, Any] = {}
        events: list[dict[str, Any]] = []

        for node_id in order:
            node = graph.nodes[node_id]["node"]
            tool = self.tools.get(node.tool)
            if tool is None:
                raise ValueError(f"Unknown tool: {node.tool}")

            params = resolve_refs(node.params, input_data=input_data, results=results)
            event: dict[str, Any] = {
                "node": node_id,
                "tool": node.tool,
                "params": params,
                "retry": node.retry,
                "timeout_sec": node.timeout_sec,
                "status": "started",
                "start_ts": time.time(),
            }
            events.append(event)

            last_err: str | None = None
            for attempt in range(node.retry + 1):
                try:
                    value = await run_tool(tool, params=params, input_data=input_data, results=results, timeout=node.timeout_sec)
                    results[node_id] = value
                    event.update(
                        {
                            "status": "completed",
                            "attempt": attempt + 1,
                            "end_ts": time.time(),
                        }
                    )
                    break
                except Exception as e:
                    last_err = str(e)
                    event.setdefault("errors", []).append({"attempt": attempt + 1, "error": last_err})
                    if attempt >= node.retry:
                        event.update({"status": "failed", "end_ts": time.time()})
                        raise
                    await asyncio.sleep(min(1.0 * (attempt + 1), 3.0))

            if last_err:
                self.log.warning("Workflow node had errors but recovered", extra={"node": node_id, "error": last_err})

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(
                {"trace_id": trace_id, "order": order, "input": input_data, "results": results, "events": events},
                ensure_ascii=False,
                indent=2,
                default=_json_serializer,
            ),
            encoding="utf-8",
        )

        return WorkflowRunResult(trace_id=trace_id, results=results, log_path=str(out_path))


async def run_tool(
    tool: ToolFn,
    *,
    params: dict[str, Any],
    input_data: dict[str, Any],
    results: dict[str, Any],
    timeout: float | None,
) -> Any:
    async def _call() -> Any:
        kwargs = dict(params)
        kwargs["context"] = {"input": input_data, "results": results}
        rv = tool(**kwargs)
        if asyncio.iscoroutine(rv) or isinstance(rv, Awaitable):
            return await rv  # type: ignore[no-any-return]
        return rv

    if timeout is None:
        return await _call()
    return await asyncio.wait_for(_call(), timeout=timeout)


def resolve_refs(obj: Any, *, input_data: dict[str, Any], results: dict[str, Any]) -> Any:
    """
    Resolve {"$ref": "input.foo"} or {"$ref": "results.nodeId.key"} inside params.
    Keeps it minimal but extensible.
    """
    if isinstance(obj, dict):
        if set(obj.keys()) == {"$ref"} and isinstance(obj["$ref"], str):
            return _get_by_path(obj["$ref"], input_data=input_data, results=results)
        return {k: resolve_refs(v, input_data=input_data, results=results) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_refs(v, input_data=input_data, results=results) for v in obj]
    return obj


def _get_by_path(path: str, *, input_data: dict[str, Any], results: dict[str, Any]) -> Any:
    if not (path.startswith("input.") or path.startswith("results.")):
        raise ValueError(f"Unsupported $ref path: {path}")

    root_name, rest = path.split(".", 1)
    cur: Any = input_data if root_name == "input" else results
    for part in rest.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(f"$ref not found: {path}")
    return cur


def _json_serializer(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    raise TypeError(f"Type {type(obj)} not serializable")


