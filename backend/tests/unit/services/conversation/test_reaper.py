"""T038: the reaper closes idle sessions even when nothing else touches the pool (FR-S06)."""

import asyncio

import pytest

from app.services.conversation import run_session_reaper

_FAST_INTERVAL = 0.01


class CountingEngine:
    def __init__(self, failures: int = 0) -> None:
        self.sweeps = 0
        self._failures = failures

    def evict_idle(self) -> None:
        self.sweeps += 1
        if self.sweeps <= self._failures:
            raise RuntimeError("sweep failed")


async def _run_for(engine, seconds: float) -> asyncio.Task:
    task = asyncio.create_task(run_session_reaper(engine, _FAST_INTERVAL))
    await asyncio.sleep(seconds)
    return task


async def test_sweeps_once_per_interval():
    engine = CountingEngine()

    task = await _run_for(engine, _FAST_INTERVAL * 8)
    task.cancel()

    assert engine.sweeps >= 3


async def test_a_failed_sweep_is_logged_and_the_loop_continues(caplog):
    engine = CountingEngine(failures=1)

    task = await _run_for(engine, _FAST_INTERVAL * 8)
    task.cancel()

    assert engine.sweeps >= 2
    assert "Idle session sweep failed" in caplog.text


async def test_cancelling_ends_the_reaper():
    task = await _run_for(CountingEngine(), _FAST_INTERVAL)

    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled()
