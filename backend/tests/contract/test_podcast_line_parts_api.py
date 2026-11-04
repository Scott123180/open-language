"""011 T035: streamed host lines and their parts' audio (contracts §4)."""

from concurrent.futures import Future

import pytest

from app.main import app
from app.podcasts.routes import get_part_wait_seconds
from app.podcasts.services.spoken_parts import SpokenParts
from app.services.factory import get_spoken_parts
from app.services.tts.base import TTSError
from tests.support.podcast_harness import EPISODES, done_of, lines_of, podcast_harness
from tests.support.synchronous_executor import SynchronousExecutor

PART_GONE = "That part of the line isn't there any more."
PART_LATE = "The line's audio took too long. Press Replay when the line has arrived."


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _parts(frames: list[dict]) -> list[dict]:
    return [frame for frame in frames if frame.get("event") == "line_part"]


def _events(frames: list[dict]) -> list[str]:
    return [frame.get("event") or ("done" if frame.get("done") else "error") for frame in frames]


def _three_sentence_line(harness, format="panel") -> tuple[int, list[dict]]:
    conversation_id = harness.start(format)
    harness.writer.script_tokens(["Hola a todos. ", "Hoy hablamos ", "de pan. ¡Qué rico!"])
    return conversation_id, harness.stream(conversation_id, "next")


def test_a_line_streams_started_then_each_part_then_the_line_and_done(harness):
    _conversation_id, frames = _three_sentence_line(harness)

    assert _events(frames) == [
        "line_started",
        "line_part",
        "line_part",
        "line_part",
        "line",
        "done",
    ]
    started, line = frames[0], lines_of(frames)[0]
    assert started["host_id"] == line["host_id"]
    assert {part["stream_id"] for part in _parts(frames)} == {started["stream_id"]}
    assert [part["index"] for part in _parts(frames)] == [0, 1, 2]


def test_the_lines_content_is_its_parts_joined_by_single_spaces(harness):
    _conversation_id, frames = _three_sentence_line(harness)

    texts = [part["text"] for part in _parts(frames)]
    assert texts == ["Hola a todos.", "Hoy hablamos de pan.", "¡Qué rico!"]
    assert lines_of(frames)[0]["content"] == " ".join(texts)


def test_each_parts_audio_is_served_as_a_wav(harness):
    conversation_id, frames = _three_sentence_line(harness)

    for part in _parts(frames):
        assert part["audio_url"].startswith(f"{EPISODES}/{conversation_id}/parts/")
        response = harness.client.get(part["audio_url"])
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"


def test_an_unknown_part_is_gone(harness):
    conversation_id, frames = _three_sentence_line(harness)
    stream_id = frames[0]["stream_id"]

    for url in (
        f"{EPISODES}/{conversation_id}/parts/{stream_id}/9",
        f"{EPISODES}/{conversation_id}/parts/unknown/0",
    ):
        response = harness.client.get(url)
        assert (response.status_code, response.json()["detail"]) == (404, PART_GONE)


def test_another_episodes_stream_is_gone(harness):
    _conversation_id, frames = _three_sentence_line(harness)
    other = harness.start("panel")

    response = harness.client.get(f"{EPISODES}/{other}/parts/{frames[0]['stream_id']}/0")

    assert (response.status_code, response.json()["detail"]) == (404, PART_GONE)


def test_an_expired_stream_is_gone(harness):
    _conversation_id, frames = _three_sentence_line(harness)
    harness.parts._clock.now += 601
    harness.parts.begin("sweep", 0, None, "")

    response = harness.client.get(_parts(frames)[0]["audio_url"])

    assert (response.status_code, response.json()["detail"]) == (404, PART_GONE)


class _NeverDone(SynchronousExecutor):
    def submit(self, fn, /, *args, **kwargs) -> Future:
        return Future()


class _Failing(SynchronousExecutor):
    def submit(self, fn, /, *args, **kwargs) -> Future:
        failed: Future = Future()
        failed.set_exception(TTSError("piper is gone"))
        return failed


def _with_parts(harness, worker, tmp_path) -> SpokenParts:
    parts = SpokenParts(worker, harness.parts._clock, tmp_path / "parts-cache", wait_seconds=0.01)
    app.dependency_overrides[get_spoken_parts] = lambda: parts
    return parts


def test_a_part_not_ready_in_time_says_to_replay_later(harness, tmp_path):
    _with_parts(harness, _NeverDone(), tmp_path)
    app.dependency_overrides[get_part_wait_seconds] = lambda: 0.01
    conversation_id = harness.start("panel")

    url = _parts(harness.stream(conversation_id, "next"))[0]["audio_url"]
    response = harness.client.get(url)

    assert (response.status_code, response.json()["detail"]) == (504, PART_LATE)


def test_a_voice_that_stopped_working_is_a_503_with_the_hosts_message(harness, tmp_path):
    _with_parts(harness, _Failing(), tmp_path)
    conversation_id = harness.start("panel")
    frames = harness.stream(conversation_id, "next")
    host = next(
        h for h in harness.episode(conversation_id)["hosts"] if h["host_id"] == frames[0]["host_id"]
    )

    response = harness.client.get(_parts(frames)[0]["audio_url"])

    assert response.status_code == 503
    assert host["name"] in response.json()["detail"]


def test_one_hosts_continue_offers_jump_in_but_not_pass(harness):
    conversation_id = harness.start("one_host")
    harness.writer.script("¡Hola a todos! Bienvenidos al programa de hoy. [@all]")

    done = done_of(harness.stream(conversation_id, "next"))

    assert (done["turn"], done["awaiting"]) == ("hosts", "continue")
    assert (done["can_jump_in"], done["can_pass"]) == (True, False)
