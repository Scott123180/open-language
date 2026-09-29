"""T105: POST /api/podcasts/shows/generate and /shows/surprise (contracts §3)."""

import random

import pytest
from sqlalchemy import text

from app.main import app
from app.podcasts.services.surprise import SurpriseTopics
from app.services.factory import get_structured_llm
from tests.support.podcast_harness import podcast_harness
from tests.support.scripted_show_llm import DECLINED_SHOW, SUITABLE_SHOW, ScriptedShowLLM

GENERATE = "/api/podcasts/shows/generate"
SURPRISE = "/api/podcasts/shows/surprise"
PREFERENCES = "/api/podcasts/preferences"
IDEA_NEEDED = "Type a few words about the show you'd like, or press Surprise me."
DECLINED = "That idea can't become a show here. Try a different topic, or press Surprise me."
PODCAST_TABLES = ("podcast_episodes", "podcast_hosts", "podcast_host_lines")


@pytest.fixture
def llm():
    return ScriptedShowLLM()


@pytest.fixture
def harness(tmp_path, llm):
    from app.podcasts.show_routes import get_surprise_topics

    with podcast_harness(tmp_path) as podcast:
        app.dependency_overrides[get_structured_llm] = lambda: llm
        app.dependency_overrides[get_surprise_topics] = lambda: SurpriseTopics(random.Random(4))
        yield podcast


def _idea_line(prompt: str) -> str:
    return next(line for line in prompt.splitlines() if line.startswith("Idea: "))


def _row_counts(harness) -> list[int]:
    session = harness.session()
    return [
        session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() for table in PODCAST_TABLES
    ]


@pytest.mark.parametrize("idea", ["   ", "x" * 201])
def test_an_empty_or_long_idea_is_refused_without_a_model_call(harness, llm, idea):
    response = harness.client.post(GENERATE, json={"idea": idea})

    assert response.status_code == 422
    assert response.json() == {"detail": IDEA_NEEDED, "can_surprise": True}
    assert llm.calls == []


def test_a_two_hundred_character_idea_is_accepted(harness):
    response = harness.client.post(GENERATE, json={"idea": "x" * 200})

    assert response.status_code == 200


def test_a_declined_idea_is_refused_with_the_offer_of_surprise_me(harness, llm):
    llm.reply = DECLINED_SHOW

    response = harness.client.post(GENERATE, json={"idea": "something nasty"})

    assert response.status_code == 422
    assert response.json() == {"detail": DECLINED, "can_surprise": True}


def test_a_suitable_idea_becomes_a_generated_draft(harness):
    response = harness.client.post(GENERATE, json={"idea": "living abroad as a nurse"})

    draft = response.json()
    assert response.status_code == 200
    assert draft["source"] == "generated"
    assert draft["show_id"] is None
    assert draft["title"] == SUITABLE_SHOW["title"]
    assert draft["language"] == "es"
    assert [host["slot"] for host in draft["hosts"]] == ["lead", "second"]


def test_the_titles_to_avoid_reach_the_prompt(harness, llm):
    body = {"idea": "football tactics", "avoid_titles": ["Tiki-Taka Talk"]}

    harness.client.post(GENERATE, json=body)

    assert "Tiki-Taka Talk" in llm.last_prompt


def test_the_saved_interests_reach_the_prompt(harness, llm):
    harness.client.put(PREFERENCES, json={"interests": ["football", "cooking"]})

    harness.client.post(GENERATE, json={"idea": "a trip to the coast"})

    assert "football" in llm.last_prompt


def test_the_hosts_never_take_the_saved_learner_name(harness):
    harness.client.put(PREFERENCES, json={"learner_name": "Lucía"})

    for _ in range(5):
        draft = harness.client.post(GENERATE, json={"idea": "a trip"}).json()
        assert "Lucía" not in [host["name"] for host in draft["hosts"]]


def test_surprise_me_returns_a_surprise_draft(harness, llm):
    response = harness.client.post(SURPRISE, json={})

    assert response.status_code == 200
    assert response.json()["source"] == "surprise"
    assert response.json()["show_id"] is None
    assert len(llm.calls) == 1


def test_surprise_me_draws_on_the_saved_interests(harness, llm):
    harness.client.put(PREFERENCES, json={"interests": ["origami"]})

    for _ in range(6):
        harness.client.post(SURPRISE, json={})

    ideas = [_idea_line(call[-1].content) for call in llm.calls]
    assert sum("origami" in idea for idea in ideas) >= 2


def test_a_declined_surprise_is_a_plain_retry(harness, llm):
    llm.reply = DECLINED_SHOW

    response = harness.client.post(SURPRISE, json={})

    assert response.status_code == 503
    assert "try again" in response.json()["detail"].lower()


@pytest.mark.parametrize("path", [GENERATE, SURPRISE])
def test_an_unreadable_reply_is_a_503_with_a_plain_retry(harness, llm, path):
    llm.raw_reply = "not json"

    response = harness.client.post(path, json={"idea": "football"})

    assert response.status_code == 503
    assert "try again" in response.json()["detail"].lower()


def test_neither_endpoint_stores_anything(harness):
    before = _row_counts(harness)

    harness.client.post(GENERATE, json={"idea": "football"})
    harness.client.post(SURPRISE, json={})

    assert _row_counts(harness) == before
