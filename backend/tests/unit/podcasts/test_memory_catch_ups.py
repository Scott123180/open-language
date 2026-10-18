"""010 T036: one catch-up per series, on the keeper it was started with (research R6)."""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from app.podcasts.services.series_memory import KeeperEndings, MemoryCatchUps

from app.podcasts.services.series_snapshot import SeriesSnapshot
from app.podcasts.services.series_storage import PendingEpisode
from app.podcasts.services.storage import EpisodeSeriesFacts
from app.services.llm.base import LLMError
from tests.support.synchronous_executor import SynchronousExecutor

SERIES_ID = 4


class FakeKeeper:
    def __init__(self, error: Exception | None = None, gate: threading.Event | None = None) -> None:
        self.caught_up: list[int] = []
        self._error = error
        self._gate = gate

    def catch_up(self, series_id: int) -> None:
        if self._gate is not None:
            self._gate.wait(timeout=5)
        self.caught_up.append(series_id)
        if self._error is not None:
            raise self._error


class FakeSeries:
    def __init__(self, pending: bool) -> None:
        self._pending = (PendingEpisode(81, 1, None),) if pending else ()

    def pending_episodes(self, series_id: int):
        return self._pending


@pytest.fixture
def catch_ups() -> MemoryCatchUps:
    return MemoryCatchUps(SynchronousExecutor())


def test_a_catch_up_starts_and_runs_on_its_keeper(catch_ups):
    keeper = FakeKeeper()

    assert catch_ups.start(SERIES_ID, keeper) == "started"
    assert keeper.caught_up == [SERIES_ID]


def test_a_second_start_while_one_runs_is_running_and_starts_nothing():
    gate = threading.Event()
    catch_ups = MemoryCatchUps(ThreadPoolExecutor(max_workers=2))
    first, second = FakeKeeper(gate=gate), FakeKeeper()

    assert catch_ups.start(SERIES_ID, first) == "started"
    assert catch_ups.start(SERIES_ID, second) == "running"
    assert catch_ups.status(SERIES_ID, FakeSeries(pending=False)) == "running"
    gate.set()
    assert catch_ups.wait(SERIES_ID, first, limit=2).status == "up_to_date"

    assert first.caught_up == [SERIES_ID] and second.caught_up == []


def test_each_catch_up_runs_on_the_keeper_it_was_started_with(catch_ups):
    ollama, claude = FakeKeeper(), FakeKeeper()

    catch_ups.start(SERIES_ID, ollama)
    catch_ups.start(SERIES_ID, claude)

    assert (ollama.caught_up, claude.caught_up) == ([SERIES_ID], [SERIES_ID])
    assert not any(isinstance(value, FakeKeeper) for value in vars(catch_ups).values())


@pytest.mark.parametrize(("pending", "status"), [(True, "pending"), (False, "up_to_date")])
def test_the_status_reflects_unread_lines_when_nothing_runs(catch_ups, pending, status):
    assert catch_ups.status(SERIES_ID, FakeSeries(pending)) == status


def test_waiting_returns_up_to_date_once_the_catch_up_finishes(catch_ups):
    outcome = catch_ups.wait(SERIES_ID, FakeKeeper(), limit=1)

    assert (outcome.status, outcome.detail) == ("up_to_date", None)


def test_waiting_reports_a_provider_failure_and_logs_it(catch_ups, caplog):
    failing = FakeKeeper(error=LLMError("connection refused", "Ollama isn't running. Start it."))

    with caplog.at_level(logging.WARNING):
        outcome = catch_ups.wait(SERIES_ID, failing, limit=1)

    assert (outcome.status, outcome.detail) == ("failed", "Ollama isn't running. Start it.")
    assert "connection refused" in caplog.text


def test_waiting_times_out_while_the_catch_up_carries_on():
    gate = threading.Event()
    catch_ups = MemoryCatchUps(ThreadPoolExecutor(max_workers=1))
    keeper = FakeKeeper(gate=gate)

    outcome = catch_ups.wait(SERIES_ID, keeper, limit=0.05)

    assert (outcome.status, outcome.detail) == ("timed_out", "It's taking longer than usual.")
    assert catch_ups.status(SERIES_ID, FakeSeries(pending=True)) == "running"
    gate.set()
    assert catch_ups.wait(SERIES_ID, keeper, limit=2).status == "up_to_date"


# --- the endings listener ----------------------------------------------------------------


class FakeEpisodes:
    def __init__(self, series: EpisodeSeriesFacts | None) -> None:
        self._series = series

    def get_episode(self, conversation_id: int):
        return type("Record", (), {"series": self._series})()


def test_a_finished_series_episode_starts_a_catch_up_with_the_endings_keeper(catch_ups):
    keeper = FakeKeeper()
    facts = EpisodeSeriesFacts(SERIES_ID, 2, SeriesSnapshot(2))

    KeeperEndings(catch_ups, FakeEpisodes(facts), keeper).episode_finished(81)

    assert keeper.caught_up == [SERIES_ID]


def test_a_finished_one_off_starts_nothing(catch_ups):
    keeper = FakeKeeper()

    KeeperEndings(catch_ups, FakeEpisodes(None), keeper).episode_finished(81)

    assert keeper.caught_up == []
