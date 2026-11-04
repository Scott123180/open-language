"""011 T036: host lines are streamed sentence by sentence, spoken part by part (FR-002a, R13)."""

import pytest
from sqlalchemy import text

from app.podcasts.services.episodes import load_episode
from app.services.llm.base import LLMError
from tests.support.podcast_harness import lines_of, podcast_harness

LINE_LOST = "The host lost their words. Press Retry."
TOKENS = ["Hola a todos. ", "Hoy hablamos ", "de pan. ¡Qué rico!"]


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _parts(frames):
    return [frame for frame in frames if frame.get("event") == "line_part"]


def _message_count(harness, conversation_id: int) -> int:
    with harness.session() as session:
        query = "SELECT count(*) FROM messages WHERE conversation_id = :id"
        return session.execute(text(query), {"id": conversation_id}).scalar_one()


def test_every_part_arrives_before_the_line(harness):
    conversation_id = harness.start("panel")
    harness.writer.script_tokens(TOKENS)

    frames = harness.stream(conversation_id, "next")

    events = [frame.get("event") for frame in frames]
    assert max(i for i, e in enumerate(events) if e == "line_part") < events.index("line")


def test_the_lines_audio_is_its_parts_joined_and_spoken_once(harness):
    conversation_id = harness.start("panel")
    harness.writer.script_tokens(TOKENS)
    frames = harness.stream(conversation_id, "next")
    for part in _parts(frames):
        assert harness.client.get(part["audio_url"]).status_code == 200

    message_id = lines_of(frames)[0]["message_id"]
    response = harness.client.get(f"/api/audio/tts/{message_id}")

    assert response.status_code == 200
    assert [spoken_text for _voice, spoken_text, _path in harness.speech.synthesized] == [
        "Hola a todos.",
        "Hoy hablamos de pan.",
        "¡Qué rico!",
    ]


def test_a_failure_after_a_part_loses_the_line_and_stores_nothing(harness):
    conversation_id = harness.start("panel")
    before = _message_count(harness, conversation_id)
    harness.writer.script_tokens(["Uno dos tres. ", "Cuatro cinco seis. ", "Siete ocho."])
    harness.writer.fail_after_tokens(2, LLMError("process exited mid-line"))

    frames = harness.stream(conversation_id, "next")

    assert [part["text"] for part in _parts(frames)] == ["Uno dos tres."]
    error = next(frame for frame in frames if "error" in frame)
    assert error == {"error": LINE_LOST, "stream_id": frames[0]["stream_id"]}
    assert _message_count(harness, conversation_id) == before
    assert not harness.engine.is_live(load_episode(harness.podcasts, conversation_id).key)
    assert harness.client.get(_parts(frames)[0]["audio_url"]).status_code == 404


def test_a_missing_voice_streams_the_line_as_text(tmp_path):
    with podcast_harness(tmp_path, installed=set()) as harness:
        conversation_id = harness.start("panel")
        harness.writer.script_tokens(TOKENS)

        frames = harness.stream(conversation_id, "next")

        assert [part["audio_url"] for part in _parts(frames)] == [None, None, None]
        assert lines_of(frames)[0]["content"] == "Hola a todos. Hoy hablamos de pan. ¡Qué rico!"
        assert harness.speech.synthesized == []


def test_a_legacy_episode_streams_and_stores_the_text_the_batched_path_did(harness):
    conversation_id = harness.legacy_episode("panel")
    lead = harness.episode(conversation_id)["hosts"][0]["name"]
    harness.writer.script(f"{lead}: ¡Hola a todos! (ríe) Hoy hablamos de pan.")

    frames = harness.stream(conversation_id, "next")

    assert [part["text"] for part in _parts(frames)] == ["¡Hola a todos! Hoy hablamos de pan."]
    stored = harness.podcasts.get_lines(conversation_id)[-1]
    assert stored.content == "¡Hola a todos! Hoy hablamos de pan."
    assert stored.host.was_trimmed is True
    assert (stored.host.ask, stored.host.addressee) == (None, None)
