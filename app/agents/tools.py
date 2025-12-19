from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable


ToolFn = Callable[..., Any]  # sync or async; must accept context=...


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    fn: ToolFn


def is_awaitable(x: Any) -> bool:
    return isinstance(x, Awaitable)  # type: ignore[arg-type]


