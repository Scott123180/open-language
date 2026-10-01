"""T042: a One host episode from start to sign-off (contracts §6, §7; US1-2, US1-3, US1-7)."""

import copy

import pytest

from app.podcasts.catalog import PODCAST_SCENARIO_ID
from tests.support.podcast_harness import EPISODES, done_of, lines_of, ready_made_draft

FINISHED = "This episode has finished."
YOUR_TURN = "It's your turn. Reply, pass or end the episode."
PANEL_ONLY_PASS = "You can pass only when it's your turn in a Panel."
LANGUAGE_CHANGED = "The practice language changed. Pick the show again."
SHORT_TARGET = 10


def _start_body(client, **overrides) -> dict:
    return {"show": ready_made_draft(client), "format": "one_host", "length": "short", **overrides}


# --- starting -------------------------------------------------------------------------


def test_starting_an_episode_creates_it_with_the_lead_host_only(podcast_client):
    response = podcast_client.client.post(EPISODES, json=_start_body(podcast_client.client))

    episode = response.json()
    assert response.status_code == 201
    assert episode["format"] == "one_host"
    assert [host["slot"] for host in episode["hosts"]] == ["lead"]
    assert (episode["turn"], episode["awaiting"]) == ("hosts", "opening")
    assert episode["lines"] == []


def test_the_episode_is_a_conversation_in_the_current_language(podcast_client):
    episode_id = podcast_client.start("one_host")

    conversation = podcast_client.conversations.get_conversation(episode_id)

    assert conversation.scenario_id == PODCAST_SCENARIO_ID
    assert conversation.target_language == "es"
    assert conversation.scenario_title == "Weekend Food Talk"


def test_starting_remembers_the_format_and_the_learner_name(podcast_client):
    podcast_client.start("panel", learner_name="Sam")

    preferences = podcast_client.client.get("/api/podcasts/preferences").json()

    assert (preferences["last_format"], preferences["learner_name"]) == ("panel", "Sam")


def _with_host(draft: dict, slot_index: int, **changes) -> dict:
    changed = copy.deepcopy(draft)
    changed["hosts"][slot_index].update(changes)
    return changed


@pytest.mark.parametrize(
    ("change", "field"),
    [
        (lambda d: _with_host(d, 0, personality_id="grumpy"), "personality"),
        (lambda d: _with_host(d, 1, voice_key="de_DE-thorsten-medium"), "voice"),
        (lambda d: _with_host(d, 1, name=d["hosts"][0]["name"]), "name"),
        (lambda d: {**d, "learner_role": "judge"}, "role"),
    ],
    ids=["personality", "voice", "same-name", "role"],
)
def test_an_invalid_draft_is_refused_with_a_plain_message(podcast_client, change, field):
    client = podcast_client.client
    body = _start_body(client)
    body["show"] = change(body["show"])

    response = client.post(EPISODES, json=body)

    assert response.status_code == 422
    assert field in response.json()["detail"]


def test_a_host_named_like_the_learner_is_refused(podcast_client):
    client = podcast_client.client
    body = _start_body(client)
    body["learner_name"] = body["show"]["hosts"][0]["name"]

    response = client.post(EPISODES, json=body)

    assert response.status_code == 422
    assert body["learner_name"] in response.json()["detail"]


def test_a_draft_for_another_language_is_refused(podcast_client):
    client = podcast_client.client
    body = _start_body(client)
    client.put("/api/settings", json={"target_language": "de"})

    response = client.post(EPISODES, json=body)

    assert (response.status_code, response.json()["detail"]) == (422, LANGUAGE_CHANGED)


# --- lines ------------------------------------------------------------------------------


def test_the_opening_is_the_leads_open_and_invites_the_learner(podcast_client):
    podcast_client.writer.script("¡Bienvenidos a Weekend Food Talk! ¿Qué cocinaste?")
    episode_id = podcast_client.start("one_host")

    frames = podcast_client.stream(episode_id, "next")

    [line] = lines_of(frames)
    lead = podcast_client.episode(episode_id)["hosts"][0]
    assert (line["intent"], line["host_id"], line["invites_learner"]) == (
        "open",
        lead["host_id"],
        True,
    )
    assert line["content"] == "¡Bienvenidos a Weekend Food Talk! ¿Qué cocinaste?"
    assert (done_of(frames)["turn"], done_of(frames)["awaiting"]) == ("learner", None)


def test_the_line_is_stored_as_it_is_streamed(podcast_client):
    episode_id = podcast_client.start("one_host")

    [line] = lines_of(podcast_client.stream(episode_id, "next"))

    stored = podcast_client.episode(episode_id)["lines"]
    assert [(s["message_id"], s["content"]) for s in stored] == [
        (line["message_id"], line["content"])
    ]


def test_next_at_the_learners_turn_is_refused(podcast_client):
    episode_id = podcast_client.start("one_host")
    podcast_client.stream(episode_id, "next")

    response = podcast_client.client.post(f"{EPISODES}/{episode_id}/next")

    assert (response.status_code, response.json()["detail"]) == (409, YOUR_TURN)


def test_a_reply_is_saved_then_answered_by_the_host(podcast_client):
    episode_id = podcast_client.start("one_host")
    podcast_client.stream(episode_id, "next")

    frames = podcast_client.say(episode_id, "Hice una paella.")

    assert frames[0]["event"] == "user_message_saved"
    assert [line["intent"] for line in lines_of(frames)] == ["discuss"]
    assert done_of(frames)["turn"] == "learner"
    speakers = [line["speaker"] for line in podcast_client.episode(episode_id)["lines"]]
    assert speakers == ["host", "learner", "host"]


def test_a_short_episode_wraps_up_at_its_length_and_carries_on(podcast_client):
    episode_id = podcast_client.start("one_host")
    podcast_client.stream(episode_id, "next")
    intents = []
    for turn in range(SHORT_TARGET):
        intents += [line["intent"] for line in lines_of(podcast_client.say(episode_id, f"R{turn}"))]

    assert intents[SHORT_TARGET - 2] == "wrap_up"
    assert intents[SHORT_TARGET - 1] == "discuss"
    assert podcast_client.episode(episode_id)["status"] == "active"


def test_ending_signs_off_and_finishes_the_episode(podcast_client):
    episode_id = podcast_client.start("one_host")
    podcast_client.stream(episode_id, "next")

    frames = podcast_client.stream(episode_id, "end")

    assert [line["intent"] for line in lines_of(frames)] == ["sign_off"]
    assert lines_of(frames)[0]["invites_learner"] is False
    assert done_of(frames)["turn"] == "finished"
    assert podcast_client.conversations.get_conversation(episode_id).status == "completed"


@pytest.mark.parametrize("action", ["next", "end"])
def test_a_finished_episode_takes_no_more_lines(podcast_client, action):
    episode_id = podcast_client.start("one_host")
    podcast_client.stream(episode_id, "end")

    response = podcast_client.client.post(f"{EPISODES}/{episode_id}/{action}")

    assert (response.status_code, response.json()["detail"]) == (409, FINISHED)


def test_passing_is_refused_in_one_host(podcast_client):
    episode_id = podcast_client.start("one_host")
    podcast_client.stream(episode_id, "next")

    response = podcast_client.client.post(f"{EPISODES}/{episode_id}/pass")

    assert (response.status_code, response.json()["detail"]) == (409, PANEL_ONLY_PASS)


def test_an_unknown_episode_is_not_found(podcast_client):
    response = podcast_client.client.post(f"{EPISODES}/999/next")

    assert (response.status_code, response.json()["detail"]) == (404, "Episode not found")


# --- a host shaped on the setup screen (T117, US5-3) ----------------------------------------


def test_a_changed_personality_is_stored_and_shapes_the_hosts_lines(podcast_client):
    from app.podcasts.catalog import PERSONALITIES

    client = podcast_client.client
    draft = _with_host(ready_made_draft(client), 0, personality_id="joker")
    episode = client.post(EPISODES, json={"show": draft, "format": "one_host", "length": "short"})

    podcast_client.stream(episode.json()["conversation_id"], "next")

    assert episode.json()["hosts"][0]["personality_id"] == "joker"
    standing_prompt = podcast_client.writer.received[-1][0]
    assert PERSONALITIES["joker"].speaking_style in standing_prompt
