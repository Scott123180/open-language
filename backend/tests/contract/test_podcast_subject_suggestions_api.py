"""011 T067a: POST /api/podcasts/subject-suggestions (contracts §8a, data-model §5.4)."""

import pytest
from sqlalchemy import text

from app.services.llm.base import LLMError
from tests.support.podcast_harness import podcast_harness

SUGGESTIONS = "/api/podcasts/subject-suggestions"
SHOW = {
    "title": "Big Little Questions",
    "premise": "Everyday curiosities, from why toast lands butter-side down onwards.",
    "topic": "everyday curiosities",
}
SERIES_GONE = "That series isn't there any more. Open the show again."
TOO_MANY = "Too many subjects to skip. Close the suggestions and try again."


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _detail(response) -> str:
    detail = response.json()["detail"]
    return (detail if isinstance(detail, str) else detail[0]["msg"]).removeprefix("Value error, ")


def _row_counts(harness) -> dict[str, int]:
    tables = ("conversations", "podcast_shows", "podcast_series", "podcast_preferences")
    with harness.session() as session:
        return {t: session.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() for t in tables}


def test_a_show_gets_up_to_three_subjects_from_the_selected_provider(harness):
    harness.subjects.reply = {"subjects": ["why cats purr", "why we hiccup", "why ice floats"]}

    response = harness.client.post(SUGGESTIONS, json={"show": SHOW})

    assert response.status_code == 200
    assert response.json() == {"subjects": ["why cats purr", "why we hiccup", "why ice floats"]}
    assert "Big Little Questions" in harness.subjects.last_prompt


def test_a_series_leaves_out_its_covered_topics(harness):
    topic = {"conversation_language": "los bostezos", "english": "yawning"}
    harness.memory.queue({"topic": topic, "about_learner": []})
    episode = harness.start_series("one_host")
    harness.play_through(episode["conversation_id"])
    harness.subjects.reply = {"subjects": ["Los bostezos", "why cats purr"]}

    series_id = episode["series"]["series_id"]
    response = harness.client.post(SUGGESTIONS, json={"show": SHOW, "series_id": series_id})

    assert response.json()["subjects"] == ["why cats purr"]
    assert "los bostezos" in harness.subjects.last_prompt


def test_an_unknown_series_is_gone(harness):
    response = harness.client.post(SUGGESTIONS, json={"show": SHOW, "series_id": 999})

    assert (response.status_code, _detail(response)) == (404, SERIES_GONE)


def test_a_series_of_another_language_is_gone(harness):
    episode = harness.start_series("one_host")
    harness.client.put("/api/settings", json={"target_language": "de"})

    response = harness.client.post(
        SUGGESTIONS, json={"show": SHOW, "series_id": episode["series"]["series_id"]}
    )

    assert (response.status_code, _detail(response)) == (404, SERIES_GONE)


def test_too_many_subjects_to_skip_is_refused(harness):
    response = harness.client.post(
        SUGGESTIONS, json={"show": SHOW, "avoid": [f"s{n}" for n in range(11)]}
    )

    assert (response.status_code, _detail(response)) == (422, TOO_MANY)


def test_a_provider_failure_is_a_503_with_its_message(harness):
    harness.subjects.error = LLMError("down", "Ollama isn't running. Start it and try again.")

    response = harness.client.post(SUGGESTIONS, json={"show": SHOW})

    assert (response.status_code, _detail(response)) == (
        503,
        "Ollama isn't running. Start it and try again.",
    )


def test_nothing_new_is_an_empty_list(harness):
    harness.subjects.reply = {"subjects": ["why bread goes stale"]}

    response = harness.client.post(
        SUGGESTIONS, json={"show": SHOW, "avoid": ["why bread goes stale"]}
    )

    assert (response.status_code, response.json()) == (200, {"subjects": []})


def test_nothing_is_stored(harness):
    harness.client.get("/api/podcasts/preferences")
    before = _row_counts(harness)
    harness.subjects.reply = {"subjects": ["why cats purr"]}

    harness.client.post(SUGGESTIONS, json={"show": SHOW})

    assert _row_counts(harness) == before
