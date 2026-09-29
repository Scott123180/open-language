"""T047: host voices and every learning tool on an episode (FR-027–FR-031)."""

from collections.abc import Iterator

import pytest

from app.main import app
from app.services.factory import get_llm
from app.services.llm.base import ChatMessage, LLMProvider
from tests.integration.conversation_levels.level_harness import wait_until
from tests.support.podcast_harness import EPISODES, lines_of, podcast_harness

MISSING_VOICE = "es_ES-davefx-medium"


class ToolLLM(LLMProvider):
    def __init__(self, response: str = "1. ¡Me encanta!\n2. No sé.") -> None:
        self._response = response
        self.calls: list[list[ChatMessage]] = []

    @property
    def model_name(self) -> str:
        return "tool-model"

    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        self.calls.append(messages)
        yield self._response

    def chat(self, messages: list[ChatMessage]) -> str:
        self.calls.append(messages)
        return self._response


@pytest.fixture
def tool_llm() -> ToolLLM:
    llm = ToolLLM()
    app.dependency_overrides[get_llm] = lambda: llm
    return llm


def _panel_lines(podcast_client) -> tuple[int, list[dict]]:
    episode_id = podcast_client.start("panel")
    lines = lines_of(podcast_client.stream(episode_id, "next"))
    lines += lines_of(podcast_client.stream(episode_id, "next"))
    return episode_id, lines


# --- voices -----------------------------------------------------------------------------


def test_each_line_is_spoken_in_its_hosts_voice(podcast_client):
    episode_id, _lines = _panel_lines(podcast_client)
    hosts = podcast_client.episode(episode_id)["hosts"]

    wait_until(lambda: len(podcast_client.speech.voice_keys) == 2)

    assert podcast_client.speech.voice_keys == [host["voice_key"] for host in hosts]


def test_the_audio_endpoint_uses_the_hosts_voice(podcast_client):
    episode_id, lines = _panel_lines(podcast_client)
    second = podcast_client.episode(episode_id)["hosts"][1]
    for line in lines:
        wait_until(lambda line=line: _audio_path(podcast_client, line) is not None)
    podcast_client.speech.synthesized.clear()
    podcast_client.conversations.set_tts_path(lines[1]["message_id"], "/missing.wav")

    response = podcast_client.client.get(f"/api/audio/tts/{lines[1]['message_id']}")

    assert response.status_code == 200
    assert podcast_client.speech.voice_keys == [second["voice_key"]]


def _audio_path(podcast_client, line: dict) -> str | None:
    return podcast_client.conversations.get_message(line["message_id"]).tts_audio_path


@pytest.fixture
def missing_voice_client(tmp_path):
    with podcast_harness(tmp_path, installed={"es_AR-daniela-high"}) as harness:
        yield harness


def test_a_missing_host_voice_is_reported_and_never_replaced(missing_voice_client):
    client = missing_voice_client.client
    body = {
        "show": {**_draft(client), "hosts": _hosts_with_voice_missing(client)},
        "format": "panel",
        "length": "short",
    }
    episode_id = client.post(EPISODES, json=body).json()["conversation_id"]
    missing_voice_client.stream(episode_id, "next")
    missing_voice_client.stream(episode_id, "next")

    hosts = missing_voice_client.episode(episode_id)["hosts"]

    silent = next(host for host in hosts if host["voice_key"] == MISSING_VOICE)
    assert silent["is_voice_available"] is False
    assert silent["name"] in silent["voice_unavailable_message"]
    assert len(missing_voice_client.podcasts.get_lines(episode_id)) == 2
    wait_until(lambda: len(missing_voice_client.speech.voice_keys) == 1)
    assert MISSING_VOICE not in missing_voice_client.speech.voice_keys


def _draft(client) -> dict:
    return client.get("/api/podcasts/catalog").json()["shows"][0]


def _hosts_with_voice_missing(client) -> list[dict]:
    lead, second = _draft(client)["hosts"]
    return [lead, {**second, "voice_key": MISSING_VOICE}]


# --- learning tools ---------------------------------------------------------------------


@pytest.mark.parametrize("tool", ["translate", "phrasing"])
def test_translation_and_phrasing_work_on_a_host_line(podcast_client, tool_llm, tool):
    _episode_id, lines = _panel_lines(podcast_client)

    response = podcast_client.client.post(
        f"/api/learning/{tool}",
        json={"message_id": lines[0]["message_id"], "content": lines[0]["content"]},
    )

    assert response.status_code == 200


def test_word_lookup_works_on_a_host_line(podcast_client, tool_llm):
    _episode_id, lines = _panel_lines(podcast_client)

    response = podcast_client.client.post(
        "/api/learning/word-lookup",
        json={"message_id": lines[0]["message_id"], "selection": "Línea"},
    )

    assert response.status_code == 200


def test_a_saved_word_is_saved_in_the_episodes_language(podcast_client, tool_llm):
    episode_id, _lines = _panel_lines(podcast_client)
    podcast_client.client.put("/api/settings", json={"target_language": "de"})

    response = podcast_client.client.post(
        "/api/vocabulary",
        json={"word": "paella", "translation": "paella", "source_conversation_id": episode_id},
    )

    assert response.json()["target_language"] == "es"


def test_the_expression_helper_works_in_an_episode(podcast_client):
    episode_id, _lines = _panel_lines(podcast_client)

    response = podcast_client.client.post(
        "/api/chat/helper",
        json={
            "message": "How do I say yes?",
            "helper_session_id": "h1",
            "conversation_id": episode_id,
        },
    )

    assert response.status_code == 200


def test_suggestions_label_the_transcript_with_host_names(podcast_client, tool_llm):
    episode_id = podcast_client.start("one_host", learner_name="Sam")
    podcast_client.stream(episode_id, "next")
    podcast_client.say(episode_id, "Hola")

    response = podcast_client.client.post(f"{EPISODES}/{episode_id}/suggestions")

    lead = podcast_client.episode(episode_id)["hosts"][0]["name"]
    prompt = tool_llm.calls[-1][-1].content
    assert response.json() == {"suggestions": ["¡Me encanta!", "No sé."][:1]}
    assert f"{lead}: " in prompt and "Sam: Hola" in prompt
