from __future__ import annotations

import logging
from typing import Any

from rich.logging import RichHandler


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers when reloading (uvicorn --reload)
    if any(isinstance(h, RichHandler) for h in root.handlers):
        return

    handler = RichHandler(rich_tracebacks=True, show_time=True, show_level=True, show_path=False)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_json(logger: logging.Logger, message: str, **fields: Any) -> None:
    # Keep it simple: RichHandler will render dict nicely.
    logger.info(f"{message} | {fields}")


