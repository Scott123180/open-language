"""Close idle sessions on a timer, so an untouched app holds no idle processes (FR-S06, R-16)."""

import asyncio
import logging
from typing import Protocol

logger = logging.getLogger(__name__)

SESSION_REAPER_INTERVAL_SECONDS = 60


class IdleSessionSweeper(Protocol):
    def evict_idle(self) -> None: ...


async def run_session_reaper(engine: IdleSessionSweeper, interval_seconds: float) -> None:
    """Sweep every `interval_seconds` until cancelled. A failed sweep is logged, not fatal."""
    loop = asyncio.get_running_loop()
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await loop.run_in_executor(None, engine.evict_idle)
        except Exception:
            logger.exception("Idle session sweep failed; the next sweep will try again")
