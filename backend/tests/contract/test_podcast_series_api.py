"""010 T038: GET /api/podcasts/series/{id} and POST .../memory (contracts §5, §8)."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from app.podcasts.series_routes import get_memory_wait_seconds
from app.podcasts.services.series_memory import MemoryCatchUps

from app.main import app
from app.services.factory import get_memory_catch_ups
from app.services.llm.base import LLMError
from tests.support.podcast_harness import podcast_harness

SERIES = "/api/podcasts/series"
DETAIL_KEYS = {
    "series_id",
    "language",
    "show",
    "episode_count",
    "next_episode_number",
    "unfinished_episode",
    "memory_status",
    "hosts",
    "remembered",
}
HOST_KEYS = {
    "slot",
    "name",
    "personality_id",
    "personality_label",
    "voice_key",
    "show_role",
    "has_history",
    "is_new_next_episode",
    "is_voice_available",
    "voice_unavailable_message",
}
SERIES_GONE = "That series isn't there any more. Open the show again."
MEMORY_REPLY = {
    "topic": {"conversation_language": "los bostezos", "english": "Why we yawn"},
    "about_learner": [
        {"conversation_language": "Odia las mañanas.", "english": "You hate mornings."}
    ],
}


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _episode_with_lines(harness) -> dict:
    episode = harness.start_series("one_host", learner_name="Sam")
    harness.stream(episode["conversation_id"], "next")
    harness.say(episode["conversation_id"], "Odio las mañanas.")
    return episode


def _series_id(harness) -> int:
    return _episode_with_lines(harness)["series"]["series_id"]


def _memory(harness, series_id: int, **params):
    return harness.client.post(f"{SERIES}/{series_id}/memory", params=params)


def _gated_catch_ups(harness):
    gate = harness.memory.gate()
    catch_ups = MemoryCatchUps(ThreadPoolExecutor(max_workers=1))
    app.dependency_overrides[get_memory_catch_ups] = lambda: catch_ups
    return gate


# --- GET /series/{id} ---------------------------------------------------------------------


def test_the_series_detail_has_the_contract_shape(harness):
    series_id = _series_id(harness)

    detail = harness.client.get(f"{SERIES}/{series_id}").json()

    assert set(detail) == DETAIL_KEYS
    assert all(set(host) == HOST_KEYS for host in detail["hosts"])
    assert [host["slot"] for host in detail["hosts"]] == ["lead", "second"]
    assert (detail["episode_count"], detail["next_episode_number"], detail["language"]) == (
        1,
        2,
        "es",
    )
    assert detail["show"]["show_id"] == "big-little-questions"
    assert detail["show"]["series"]["series_id"] == series_id


def test_unread_lines_make_the_memory_pending(harness):
    series_id = _series_id(harness)

    assert harness.client.get(f"{SERIES}/{series_id}").json()["memory_status"] == "pending"


def test_remembered_points_are_listed_in_english_with_their_episode(harness):
    series_id = _series_id(harness)
    harness.memory.queue(MEMORY_REPLY)
    _memory(harness, series_id)

    detail = harness.client.get(f"{SERIES}/{series_id}").json()

    assert detail["memory_status"] == "up_to_date"
    (topic,) = detail["remembered"]["topics"]
    (learner,) = detail["remembered"]["about_learner"]
    assert (topic["text"], topic["episode_number"]) == ("Why we yawn", 1)
    assert (learner["text"], learner["episode_number"]) == ("You hate mornings.", 1)
    assert isinstance(topic["point_id"], int)


def test_an_unknown_series_is_a_plain_404(harness):
    response = harness.client.get(f"{SERIES}/999")

    assert response.status_code == 404
    assert response.json()["detail"] == SERIES_GONE


# --- POST /series/{id}/memory --------------------------------------------------------------


def test_a_catch_up_starts_with_202(harness):
    series_id = _series_id(harness)

    response = _memory(harness, series_id)

    assert (response.status_code, response.json()) == (202, {"status": "started"})


def test_a_catch_up_with_nothing_to_read_is_up_to_date(harness):
    series_id = _series_id(harness)
    _memory(harness, series_id)

    response = _memory(harness, series_id)

    assert (response.status_code, response.json()) == (202, {"status": "up_to_date"})


def test_a_catch_up_already_running_is_reported(harness):
    series_id = _series_id(harness)
    gate = _gated_catch_ups(harness)

    first, second = _memory(harness, series_id), _memory(harness, series_id)
    gate.set()

    assert (first.json()["status"], second.json()["status"]) == ("started", "running")


def test_waiting_returns_up_to_date_with_200(harness):
    series_id = _series_id(harness)

    response = _memory(harness, series_id, wait="true")

    assert response.status_code == 200
    assert response.json()["status"] == "up_to_date"


def test_waiting_reports_a_provider_failure_with_its_message(harness):
    series_id = _series_id(harness)
    harness.memory.queue(LLMError("connection refused", "Ollama isn't running. Start it."))

    response = _memory(harness, series_id, wait="true")

    assert response.json() == {"status": "failed", "detail": "Ollama isn't running. Start it."}


def test_waiting_times_out_at_the_limit(harness):
    series_id = _series_id(harness)
    gate = _gated_catch_ups(harness)
    app.dependency_overrides[get_memory_wait_seconds] = lambda: 0.1

    response = _memory(harness, series_id, wait="true")
    gate.set()

    assert response.json() == {"status": "timed_out", "detail": "It's taking longer than usual."}


def test_catching_up_an_unknown_series_is_a_404(harness):
    assert _memory(harness, 999).status_code == 404
    assert _memory(harness, 999, wait="true").status_code == 404
