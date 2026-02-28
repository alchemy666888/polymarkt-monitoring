from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def with_retries(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
    logger: logging.Logger | None = None,
) -> T:
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    delay = base_delay_seconds
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception:  # noqa: BLE001 - caller supplies external I/O ops
            if attempt == attempts:
                raise
            if logger:
                logger.warning(
                    "retrying operation",
                    extra={"attempt": attempt, "remaining_attempts": attempts - attempt},
                    exc_info=True,
                )
            time.sleep(delay)
            delay *= backoff_multiplier

    raise RuntimeError("unreachable")
