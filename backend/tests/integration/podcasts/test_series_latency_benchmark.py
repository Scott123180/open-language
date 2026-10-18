"""SC-006 and the catch-up wait: a long series starts as fast as a new one (research R12).

Hand-run against the real default model, deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k series_latency

- First line: the median time to the first `line` frame of a series' episode 1, over ten fresh
  series, against episode 10 and later of one series whose memory is full (SC-006: within 20%).
  The full memory is written straight to storage, at the caps and the text budget. Each episode's
  session is warmed first, as the episode screen does on load.
- Catch-up wait: `?wait=true` straight after a Medium episode's sign-off, ten runs (p90 ≤ 15 s).
"""

import statistics

import pytest

from app.podcasts.catalog import (
    MAX_REMEMBERED_ABOUT_LEARNER,
    MAX_REMEMBERED_TOPICS,
    REMEMBERED_TEXT_BUDGET,
)
from app.podcasts.services.series_storage import MemoryReply, PointText
from app.podcasts.services.sqlite_series_storage import SQLiteSeriesStorage
from tests.integration.podcasts.podcast_harness import real_podcast_app
from tests.integration.podcasts.series_benchmark import (
    end,
    play,
    start_series,
    wait_for_memory,
    warm,
)

pytestmark = pytest.mark.benchmark

RUNS = 10
EPISODES_BEFORE_TEN = 9
SC_006_RATIO = 1.2
CATCH_UP_P90_SECONDS = 15.0
PERCENTILE_90 = 9
SHOW = "big-little-questions"
POINT = "Le encanta hablar de la historia de su ciudad y de los mercados del barrio {n}."


def _first_line_seconds(client, show_id: str) -> float:
    episode = start_series(client, show_id, "one_host")
    warm(client, episode["conversation_id"])
    return play(client, episode["conversation_id"], [], 1).first_line_seconds


def _episode_one_medians(tmp_path) -> float:
    times = []
    for run in range(RUNS):
        with real_podcast_app(tmp_path / f"first-{run}", "es") as harness:
            times.append(_first_line_seconds(harness.client, SHOW))
    return statistics.median(times)


def _fill_memory(harness, series_id: int, conversation_ids: list[int]) -> None:
    storage = SQLiteSeriesStorage(harness.sessions())
    per_point = REMEMBERED_TEXT_BUDGET // (MAX_REMEMBERED_TOPICS + MAX_REMEMBERED_ABOUT_LEARNER)
    for n, conversation_id in enumerate(conversation_ids):
        topic = PointText(POINT.format(n=n)[:per_point], "t")
        learner = tuple(PointText(POINT.format(n=f"{n}{k}")[:per_point], "l") for k in range(2))
        storage.remember(series_id, conversation_id, MemoryReply(topic, learner), None)


def _later_episode_medians(tmp_path) -> float:
    with real_podcast_app(tmp_path / "long-series", "es") as harness:
        episodes = [
            start_series(harness.client, SHOW, "one_host") for _ in range(EPISODES_BEFORE_TEN)
        ]
        _fill_memory(
            harness, episodes[0]["series"]["series_id"], [e["conversation_id"] for e in episodes]
        )
        times = [_first_line_seconds(harness.client, SHOW) for _ in range(RUNS)]
    return statistics.median(times)


def test_episode_ten_starts_within_twenty_percent_of_episode_one(tmp_path):
    first = _episode_one_medians(tmp_path)
    later = _later_episode_medians(tmp_path)

    summary = f"SC-006 median first line: episode 1 {first:.2f}s, episode 10+ {later:.2f}s"
    print(f"\n{summary}")  # noqa: T201
    assert later <= first * SC_006_RATIO


def test_the_catch_up_after_a_medium_episode_is_quick(tmp_path):
    waits = []
    with real_podcast_app(tmp_path / "catch-up", "es") as harness:
        for _run in range(RUNS):
            episode = start_series(harness.client, SHOW, "one_host", length="medium")
            play(harness.client, episode["conversation_id"], ["Odio las mañanas."], 40)
            end(harness.client, episode["conversation_id"])
            outcome, seconds = wait_for_memory(harness.client, episode["series"]["series_id"])
            waits.append(seconds)
            print(f"catch-up wait {seconds:.2f}s ({outcome['status']})")  # noqa: T201
    p90 = statistics.quantiles(waits, n=10)[PERCENTILE_90 - 1]
    print(f"\nCatch-up wait p90 {p90:.2f}s")  # noqa: T201
    assert p90 <= CATCH_UP_P90_SECONDS
