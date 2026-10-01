"""T066: a Listen episode, two hosts and Continue, to the sign-off (FR-015, FR-016, FR-019, US2)."""

import pytest

from tests.support.podcast_harness import EPISODES, done_of, lines_of

LISTENING = "This is a listening episode. Start the show in One host or Panel to speak."
MAX_RUN = 3


def _play_to_the_end(podcast_client, episode_id: int) -> list[tuple[dict, dict]]:
    """Press Continue until the episode finishes; return every (line, done) pair."""
    played = []
    for _press in range(40):
        frames = podcast_client.stream(episode_id, "next")
        played.append((lines_of(frames)[0], done_of(frames)))
        if done_of(frames)["turn"] == "finished":
            return played
    raise AssertionError("the Listen episode never finished")


@pytest.fixture
def played(podcast_client):
    episode_id = podcast_client.start("listen")
    return episode_id, _play_to_the_end(podcast_client, episode_id)


def test_both_hosts_take_part(podcast_client):
    episode_id = podcast_client.start("listen")

    assert [host["slot"] for host in podcast_client.episode(episode_id)["hosts"]] == [
        "lead",
        "second",
    ]


def test_the_lead_opens_and_the_second_host_greets(podcast_client, played):
    episode_id, lines = played
    lead, second = podcast_client.episode(episode_id)["hosts"]

    assert [(line["intent"], line["host_id"]) for line, _done in lines[:2]] == [
        ("open", lead["host_id"]),
        ("greet", second["host_id"]),
    ]


def test_every_line_waits_for_continue_and_none_invites_the_learner(played):
    _episode_id, lines = played

    assert all((done["turn"], done["awaiting"]) == ("hosts", "continue") for _l, done in lines[:-1])
    assert not any(line["invites_learner"] for line, _done in lines)


def test_a_short_episode_wraps_up_then_signs_off_and_finishes(podcast_client, played):
    episode_id, lines = played
    intents = [line["intent"] for line, _done in lines]

    assert 10 <= intents.index("wrap_up") + 1 <= 12
    assert intents[-2:] == ["wrap_up", "sign_off"]
    assert lines[-1][1]["turn"] == "finished"
    assert podcast_client.conversations.get_conversation(episode_id).status == "completed"


def test_no_host_speaks_more_than_three_lines_in_a_row(played):
    _episode_id, lines = played
    speakers = [line["host_id"] for line, _done in lines]

    runs = [len(set(speakers[i : i + MAX_RUN + 1])) for i in range(len(speakers) - MAX_RUN)]
    assert all(distinct > 1 for distinct in runs)


@pytest.mark.parametrize("action", ["message", "pass", "suggestions"])
def test_the_learner_cannot_speak_pass_or_ask_for_suggestions(podcast_client, action):
    episode_id = podcast_client.start("listen")
    podcast_client.stream(episode_id, "next")
    body = {"content": "Hola"} if action == "message" else None

    response = podcast_client.client.post(f"{EPISODES}/{episode_id}/{action}", json=body)

    assert response.status_code == 409
    if action != "pass":
        assert response.json()["detail"] == LISTENING


def test_ending_mid_episode_signs_off(podcast_client):
    episode_id = podcast_client.start("listen")
    podcast_client.stream(episode_id, "next")

    frames = podcast_client.stream(episode_id, "end")

    assert [line["intent"] for line in lines_of(frames)] == ["sign_off"]
    assert done_of(frames)["turn"] == "finished"
