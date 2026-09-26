"""T038: the app's lifespan runs one session reaper and closes every session on shutdown."""

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.services.conversation import SESSION_REAPER_INTERVAL_SECONDS


class RecordingEngine:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def evict_idle(self) -> None:
        """The recording reaper never sweeps."""

    def close(self) -> None:
        self._events.append("engine closed")


@pytest.fixture()
def lifecycle(monkeypatch) -> dict:
    record: dict = {"events": [], "reapers": []}
    engine = RecordingEngine(record["events"])

    async def recording_reaper(reaper_engine, interval_seconds):
        record["reapers"].append((reaper_engine, interval_seconds))
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            record["events"].append("reaper cancelled")
            raise

    monkeypatch.setattr(main_module, "get_conversation_engine", lambda: engine)
    monkeypatch.setattr(main_module, "run_session_reaper", recording_reaper)
    record["engine"] = engine
    return record


def _wait_for_reaper_start(lifecycle) -> None:
    deadline = time.monotonic() + 2
    while not lifecycle["reapers"]:
        assert time.monotonic() < deadline, "the reaper never started"
        time.sleep(0.01)


def test_reaper_interval_is_one_minute():
    assert SESSION_REAPER_INTERVAL_SECONDS == 60


def test_startup_runs_exactly_one_reaper_over_the_engine(lifecycle):
    with TestClient(main_module.app):
        _wait_for_reaper_start(lifecycle)

    assert lifecycle["reapers"] == [(lifecycle["engine"], SESSION_REAPER_INTERVAL_SECONDS)]


def test_shutdown_cancels_the_reaper_then_closes_the_engine_once(lifecycle):
    with TestClient(main_module.app):
        _wait_for_reaper_start(lifecycle)
        assert lifecycle["events"] == []

    assert lifecycle["events"] == ["reaper cancelled", "engine closed"]
