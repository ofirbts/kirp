from __future__ import annotations

import logging
from typing import Any

from src.core.structured_logging import log_json


def log_control_plane(
    logger: logging.Logger,
    level: str,
    event: str,
    **fields: Any,
) -> None:
    log_json(logger, level, event, control_plane=1, **fields)
