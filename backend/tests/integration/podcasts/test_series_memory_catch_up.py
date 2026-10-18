"""010 T041: memory is caught up after a sign-off and on request, by the selected provider (R6)."""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from app.podcasts.series_routes import get_memory_wait_seconds
from app.podcasts.services.series_memory import MemoryCatchUps, SeriesMemoryKeeper
from fastapi import Depends

from app.main import app
from app.podcasts.models import PodcastSeriesEpisode, PodcastSeriesMemory
from app.services.factory import (
    get_app_settings,
    get_memory_catch_ups,
    get_series_memory_keeper,
    get_structured_llm,
    memory_stores,
)
from app.services.llm.base import LLMError
from app.services.storage.base import AppSettingsRecord
from tests.support.podcast_harness import CATALOG, podcast_harness
from tests.support.scripted_memory_llm import ScriptedMemoryLLM

SERIES = "/api/podcasts/series"
TOPIC_ONLY = {
    "topic": {"conversation_language": "los bostezos", "english": "Why we yawn"},
    "about_learner": [],
}
WITH_LEARNER = {
    "topic": {"conversation_language": "el sueño", "english": "Sleep"},
    "about_learner": [
        {"conversation_language": "Odia las mañanas.", "english": "You hate mornings."}
    ],
}


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _memories(harness) -> list[tuple[str, str]]:
    rows = harness.session().query(PodcastSeriesMemory).order_by(PodcastSeriesMemory.id).all()
    return [(row.kind, row.conversation_language) for row in rows]


def _marker(harness, conversation_id: int) -> int | None:
    return harness.session().get(PodcastSeriesEpisode, conversation_id).remembered_up_to_message_id


def _talk(harness, conversation_id: int) -> None:
    harness.stream(conversation_id, "next")
    harness.say(conversation_id, "Odio las mañanas.")


def test_a_series_sign_off_catches_up_the_episode(harness):
    harness.memory.queue(WITH_LEARNER)
    episode = harness.start_series(learner_name="Sam")
    _talk(harness, episode["conversation_id"])

    harness.stream(episode["conversation_id"], "end")

    assert _memories(harness) == [("topic", "el sueño"), ("learner", "Odia las mañanas.")]
    last_line = harness.episode(episode["conversation_id"])["lines"][-1]["message_id"]
    assert _marker(harness, episode["conversation_id"]) == last_line


def test_a_one_off_sign_off_catches_up_nothing(harness):
    conversation_id = harness.start("one_host", learner_name="Sam")
    harness.stream(conversation_id, "next")
    harness.say(conversation_id, "Hola.")

    harness.stream(conversation_id, "end")

    assert harness.memory.calls == []


def test_a_second_catch_up_reads_only_the_new_lines(harness):
    episode = harness.start_series(learner_name="Sam")
    conversation_id, series_id = episode["conversation_id"], episode["series"]["series_id"]
    harness.stream(conversation_id, "next")
    harness.say(conversation_id, "Primera frase del oyente.")
    harness.client.post(f"{SERIES}/{series_id}/memory")
    harness.say(conversation_id, "Segunda frase del oyente.")

    harness.client.post(f"{SERIES}/{series_id}/memory")

    assert "Primera frase" in harness.memory.prompts[0]
    assert (
        "Primera frase" not in harness.memory.prompts[1].split("Transcript:")[1].split("Already")[0]
    )
    assert "Segunda frase" in harness.memory.prompts[1]


def test_a_listen_episode_remembers_a_topic_and_nothing_about_the_learner(harness):
    harness.memory.queue(WITH_LEARNER)
    episode = harness.start_series("listen")
    harness.stream(episode["conversation_id"], "next")
    harness.stream(episode["conversation_id"], "next")

    harness.client.post(f"{SERIES}/{episode['series']['series_id']}/memory")

    assert _memories(harness) == [("topic", "el sueño")]


def test_a_provider_failure_changes_nothing_and_is_logged(harness, caplog):
    episode = harness.start_series(learner_name="Sam")
    _talk(harness, episode["conversation_id"])
    harness.memory.queue(LLMError("connection refused", "Ollama isn't running."))

    with caplog.at_level(logging.WARNING):
        harness.client.post(f"{SERIES}/{episode['series']['series_id']}/memory")

    assert _memories(harness) == []
    assert _marker(harness, episode["conversation_id"]) is None
    assert "connection refused" in caplog.text


def test_a_catch_up_uses_the_provider_selected_at_that_moment(harness):
    ollama, claude = ScriptedMemoryLLM(), ScriptedMemoryLLM()

    def selected(settings: AppSettingsRecord = Depends(get_app_settings)):
        return claude if settings.llm_provider == "claude" else ollama

    app.dependency_overrides[get_structured_llm] = selected
    del app.dependency_overrides[get_series_memory_keeper]
    episode = harness.start_series(learner_name="Sam")
    _talk(harness, episode["conversation_id"])
    harness.conversations.update_settings(llm_provider="claude", llm_model="sonnet")

    harness.client.post(f"{SERIES}/{episode['series']['series_id']}/memory")

    assert len(claude.calls) == 1 and ollama.calls == []


def test_waiting_brings_the_next_start_the_new_points(harness):
    harness.memory.queue(WITH_LEARNER)
    episode = harness.start_series(learner_name="Sam")
    _talk(harness, episode["conversation_id"])

    waited = harness.client.post(f"{SERIES}/{episode['series']['series_id']}/memory?wait=true")
    harness.start_series(learner_name="Sam")

    assert waited.json()["status"] == "up_to_date"
    snapshot = (
        harness.session()
        .query(PodcastSeriesEpisode)
        .order_by(PodcastSeriesEpisode.episode_number.desc())
        .first()
        .snapshot
    )
    assert "Odia las mañanas." in snapshot and "el sueño" in snapshot


def test_a_timed_out_wait_never_blocks_other_requests(harness):
    episode = harness.start_series(learner_name="Sam")
    _talk(harness, episode["conversation_id"])
    blocked = ScriptedMemoryLLM()
    gate = blocked.gate()
    catch_ups = MemoryCatchUps(ThreadPoolExecutor(max_workers=1))
    app.dependency_overrides[get_memory_catch_ups] = lambda: catch_ups
    app.dependency_overrides[get_series_memory_keeper] = lambda: SeriesMemoryKeeper(
        blocked, memory_stores(harness.sessions)
    )
    app.dependency_overrides[get_memory_wait_seconds] = lambda: 1.0
    results: dict = {}

    def wait() -> None:
        results["wait"] = harness.client.post(
            f"{SERIES}/{episode['series']['series_id']}/memory?wait=true"
        ).json()

    waiter = threading.Thread(target=wait)
    waiter.start()
    _until(lambda: blocked.calls)
    catalog = harness.client.get(CATALOG)
    is_still_waiting = waiter.is_alive()
    waiter.join(timeout=5)
    gate.set()

    assert catalog.status_code == 200 and is_still_waiting
    assert results["wait"]["status"] == "timed_out"


def _until(condition, limit: float = 2.0) -> None:
    deadline = time.monotonic() + limit
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.01)
