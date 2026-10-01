"""T045: every stored line is one host's words, and one line is made at a time (FR-012, R4, R12)."""

import threading

import pytest

from app.services.llm.base import LLMError
from tests.support.podcast_harness import EPISODES, lines_of

NOT_RESPONDING = "The AI is not responding. Please try again."
ALREADY_ON_ITS_WAY = "A line is already on its way."


def _second_host(podcast_client, episode_id: int) -> str:
    return podcast_client.episode(episode_id)["hosts"][1]["name"]


@pytest.mark.parametrize("label", ["second-host", "Invitado"])
def test_a_leaked_label_is_cut_before_the_line_is_stored_or_streamed(podcast_client, label):
    episode_id = podcast_client.start("panel")
    speaker = _second_host(podcast_client, episode_id) if label == "second-host" else label
    podcast_client.writer.script(f"¡Bienvenidos! {speaker}: ¡Hola!")

    [line] = lines_of(podcast_client.stream(episode_id, "next"))

    assert line["content"] == "¡Bienvenidos!"
    [stored] = podcast_client.podcasts.get_lines(episode_id)
    assert (stored.content, stored.host.was_trimmed) == ("¡Bienvenidos!", True)


def test_a_clean_line_is_not_marked_trimmed(podcast_client):
    podcast_client.writer.script("¡Bienvenidos!")
    episode_id = podcast_client.start("panel")

    podcast_client.stream(episode_id, "next")

    assert podcast_client.podcasts.get_lines(episode_id)[0].host.was_trimmed is False


def test_an_all_label_line_is_written_again_once(podcast_client):
    episode_id = podcast_client.start("panel")
    podcast_client.writer.script(f"{_second_host(podcast_client, episode_id)}: ¡Hola!", "¡Hola!")

    [line] = lines_of(podcast_client.stream(episode_id, "next"))

    assert line["content"] == "¡Hola!"
    assert len(podcast_client.writer.received) == 2


def test_a_second_empty_line_is_an_error_and_nothing_is_stored(podcast_client):
    episode_id = podcast_client.start("panel")
    podcast_client.writer.script(
        f"{_second_host(podcast_client, episode_id)}: ¡Hola!", "Invitado: ¿Qué?"
    )

    frames = podcast_client.stream(episode_id, "next")

    assert [set(frame) for frame in frames] == [{"error"}]
    assert podcast_client.podcasts.get_lines(episode_id) == ()


def test_a_provider_failure_sends_its_message_and_stores_nothing(podcast_client):
    podcast_client.writer.fail_next(LLMError("down", NOT_RESPONDING, can_retry=False))
    episode_id = podcast_client.start("panel")

    frames = podcast_client.stream(episode_id, "next")

    assert frames == [{"error": NOT_RESPONDING}]
    assert podcast_client.podcasts.get_lines(episode_id) == ()


def test_next_after_a_failure_retries_the_same_line(podcast_client):
    podcast_client.writer.fail_next(LLMError("down", NOT_RESPONDING, can_retry=False))
    episode_id = podcast_client.start("panel")
    podcast_client.stream(episode_id, "next")

    [line] = lines_of(podcast_client.stream(episode_id, "next"))

    assert line["intent"] == "open"


def test_two_presses_at_once_make_exactly_one_line(podcast_client):
    episode_id = podcast_client.start("panel")
    gate = podcast_client.writer.gate()
    statuses: list[int] = []

    def press() -> None:
        with podcast_client.client.stream("POST", f"{EPISODES}/{episode_id}/next") as response:
            response.read()
            statuses.append(response.status_code)

    first = threading.Thread(target=press)
    first.start()
    _wait_for_line_in_progress(podcast_client, episode_id)
    second = podcast_client.client.post(f"{EPISODES}/{episode_id}/next")
    gate.set()
    first.join(timeout=5)

    assert (second.status_code, second.json()["detail"]) == (409, ALREADY_ON_ITS_WAY)
    assert statuses == [200]
    assert len(podcast_client.podcasts.get_lines(episode_id)) == 1


def _wait_for_line_in_progress(podcast_client, episode_id: int) -> None:
    from app.services.factory import get_episode_locks
    from tests.integration.conversation_levels.level_harness import wait_until

    wait_until(lambda: get_episode_locks().is_held(episode_id))
