"""SC-014: a summary appears within 10 s in 90% of cases, on the default local setup.

Hand-run against the real default model, deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/conversation_summary

It summarises 10 roleplay conversations and 10 podcast episodes, in both languages, prints each
summary for `specs/007-podcast-mode/summary-review-sheet.md` (SC-012, SC-013), then checks the
p90 time. Nothing is printed after the assertion, so a miss still leaves the evidence.
"""

import statistics
import time

import pytest

from app.practice_languages import PRACTICE_LANGUAGES
from tests.integration.podcasts.podcast_harness import real_podcast_app

pytestmark = pytest.mark.benchmark

SC_014_P90_SECONDS = 10.0
LEARNER_TURNS = 4
ROLEPLAYS = (
    "order-at-restaurant",
    "buy-train-ticket",
    "check-into-hotel",
    "rent-a-car",
    "visit-pharmacy",
)
EPISODES = (("one_host", 0), ("panel", 1), ("listen", 2), ("panel", 3), ("one_host", 4))


def _timed_summary(harness, conversation_id: int) -> tuple[float, dict]:
    started = time.perf_counter()
    body = harness.client.get(f"/api/conversations/{conversation_id}/summary").json()
    return time.perf_counter() - started, body


def _conversations(harness) -> list[tuple[str, int]]:
    roleplays = [("roleplay", _roleplay(harness, scenario)) for scenario in ROLEPLAYS]
    episodes = [
        ("podcast", harness.run_episode(format, show, LEARNER_TURNS).conversation_id)
        for format, show in EPISODES
    ]
    return roleplays + episodes


def _roleplay(harness, scenario: str) -> int:
    harness.roleplay_replies(scenario, LEARNER_TURNS)
    return harness.client.get("/api/conversations").json()[0]["id"]


@pytest.mark.parametrize("language", list(PRACTICE_LANGUAGES))
def test_summaries_arrive_within_ten_seconds(tmp_path, language):
    with real_podcast_app(tmp_path, language) as harness:
        timed = [(kind, *_timed_summary(harness, cid)) for kind, cid in _conversations(harness)]
    for kind, seconds, body in timed:
        print(f"\n[{language} {kind} {seconds:.1f}s] {body.get('points', body)}")  # noqa: T201
    p90 = statistics.quantiles([seconds for _kind, seconds, _body in timed], n=10)[8]
    print(f"\nSC-014 {language}: p90 {p90:.1f}s over {len(timed)} summaries")  # noqa: T201
    assert p90 <= SC_014_P90_SECONDS
