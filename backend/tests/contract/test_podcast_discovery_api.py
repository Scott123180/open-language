"""010 T122: POST /api/podcasts/shows/discover (contracts §4)."""

import pytest

from app.main import app
from app.services.factory import get_structured_llm
from app.services.llm.base import LLMError
from tests.support.podcast_harness import podcast_harness
from tests.support.scripted_memory_llm import ScriptedMemoryLLM
from tests.support.scripted_show_llm import SUITABLE_SHOW

DISCOVER = "/api/podcasts/shows/discover"
NOT_ENOUGH = "Find a new show didn't come up with enough shows this time. Please try again."
DRAFT_KEYS = {
    "source",
    "show_id",
    "saved_show_id",
    "title",
    "premise",
    "topic",
    "learner_role",
    "language",
    "hosts",
}


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


@pytest.fixture
def llm(harness) -> ScriptedMemoryLLM:
    scripted = ScriptedMemoryLLM()
    app.dependency_overrides[get_structured_llm] = lambda: scripted
    return scripted


def _shows(*titles: str) -> dict:
    return {"shows": [{**SUITABLE_SHOW, "title": title} for title in titles]}


def test_discovery_returns_three_to_five_suggested_drafts(harness, llm):
    llm.queue(_shows("Uno", "Dos", "Tres", "Cuatro"))

    response = harness.client.post(DISCOVER, json={"avoid_titles": []})

    assert response.status_code == 200
    suggestions = response.json()["suggestions"]
    assert 3 <= len(suggestions) <= 5
    assert all(set(s) == DRAFT_KEYS and s["source"] == "suggested" for s in suggestions)


def test_too_few_suggestions_is_a_plain_503(harness, llm):
    llm.queue(_shows("Uno"), _shows("Dos"))

    response = harness.client.post(DISCOVER, json={"avoid_titles": []})

    assert (response.status_code, response.json()["detail"]) == (503, NOT_ENOUGH)


def test_a_provider_failure_is_the_providers_503(harness, llm):
    llm.queue(LLMError("refused", "Ollama isn't running. Start it and try again."))

    response = harness.client.post(DISCOVER, json={"avoid_titles": []})

    assert response.status_code == 503
    assert response.json()["detail"] == "Ollama isn't running. Start it and try again."


@pytest.mark.parametrize("titles", [["t"] * 51, ["x" * 201]], ids=["too-many", "too-long"])
def test_an_oversized_avoid_list_is_a_422(harness, llm, titles):
    assert harness.client.post(DISCOVER, json={"avoid_titles": titles}).status_code == 422
