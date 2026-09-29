"""T095: a Panel episode: Jump in, Pass, the addressed host and the settle invite (FR-013–FR-018)."""

from app.podcasts.prompts import PRODUCER_NOTE_MARKER
from tests.support.podcast_harness import EPISODES, done_of, lines_of

DEADLINE = 4
PASS_ONLY_IN_PANEL = "You can pass only when it's your turn in a Panel."


def _advance(podcast_client, episode_id: int, reply: str = "Sí, claro.") -> list[dict]:
    """One step: reply at the learner's turn, press Continue at the hosts'."""
    state = podcast_client.episode(episode_id)
    if state["turn"] == "learner":
        return podcast_client.say(episode_id, reply)
    return podcast_client.stream(episode_id, "next")


def test_the_lead_opens_and_the_second_host_greets(podcast_client):
    episode_id = podcast_client.start("panel")
    lead, second = podcast_client.episode(episode_id)["hosts"]

    [opening] = lines_of(podcast_client.stream(episode_id, "next"))
    podcast_client.stream(episode_id, "pass" if opening["invites_learner"] else "next")
    greeting = podcast_client.episode(episode_id)["lines"][1]

    assert (opening["intent"], opening["host_id"]) == ("open", lead["host_id"])
    assert (greeting["intent"], greeting["host_id"]) == ("greet", second["host_id"])


def test_the_learner_is_invited_within_four_host_lines_every_time(podcast_client):
    episode_id = podcast_client.start("panel", length="long")
    for step in range(60):
        _advance(podcast_client, episode_id, f"Respuesta {step}.")

    run = 0
    for line in podcast_client.episode(episode_id)["lines"]:
        run = 0 if line["speaker"] == "learner" else run + 1
        assert run <= DEADLINE
        assert run < DEADLINE or line["invites_learner"]


def test_jump_in_and_pass_follow_the_turn(podcast_client):
    episode_id = podcast_client.start("panel")
    for _step in range(12):
        frames = _advance(podcast_client, episode_id)
        done = done_of(frames)
        assert done["can_jump_in"] == (done["turn"] == "hosts" and done["awaiting"] == "continue")
        assert done["can_pass"] == (done["turn"] == "learner")


def _at_hosts_continue(podcast_client, episode_id: int) -> None:
    for _step in range(12):
        state = podcast_client.episode(episode_id)
        if (state["turn"], state["awaiting"]) == ("hosts", "continue"):
            return
        _advance(podcast_client, episode_id)
    raise AssertionError("the hosts never had the floor")


def test_jumping_in_is_saved_and_answered_at_once(podcast_client):
    episode_id = podcast_client.start("panel")
    _at_hosts_continue(podcast_client, episode_id)

    frames = podcast_client.say(episode_id, "¡Perdón, una pregunta!")

    assert frames[0]["event"] == "user_message_saved"
    assert len(lines_of(frames)) == 1
    speakers = [line["speaker"] for line in podcast_client.episode(episode_id)["lines"]]
    assert speakers[-2:] == ["learner", "host"]


def _at_learners_turn(podcast_client, episode_id: int) -> None:
    for _step in range(12):
        if podcast_client.episode(episode_id)["turn"] == "learner":
            return
        podcast_client.stream(episode_id, "next")
    raise AssertionError("the learner was never invited")


def test_passing_marks_the_invitation_and_the_hosts_carry_on(podcast_client):
    episode_id = podcast_client.start("panel")
    _at_learners_turn(podcast_client, episode_id)
    invitation = podcast_client.episode(episode_id)["lines"][-1]

    frames = podcast_client.stream(episode_id, "pass")

    assert len(lines_of(frames)) == 1
    stored = {line.message_id: line for line in podcast_client.podcasts.get_lines(episode_id)}
    assert stored[invitation["message_id"]].host.is_passed is True
    _prompt, pending = podcast_client.writer.received[-1]
    assert "Don't wait for" in pending[-1].content


def test_passing_at_the_hosts_turn_is_refused(podcast_client):
    episode_id = podcast_client.start("panel")
    _at_hosts_continue(podcast_client, episode_id)

    response = podcast_client.client.post(f"{EPISODES}/{episode_id}/pass")

    assert (response.status_code, response.json()["detail"]) == (409, PASS_ONLY_IN_PANEL)


def test_the_named_host_answers(podcast_client):
    episode_id = podcast_client.start("panel")
    second = podcast_client.episode(episode_id)["hosts"][1]
    _at_learners_turn(podcast_client, episode_id)

    frames = podcast_client.say(episode_id, f"{second['name']}, ¿y tú qué opinas?")

    assert lines_of(frames)[0]["host_id"] == second["host_id"]


def test_an_invitation_after_two_hosts_asks_the_learner_to_settle_it(podcast_client):
    episode_id = podcast_client.start("panel", length="long")
    for step in range(60):
        _advance(podcast_client, episode_id, f"Respuesta {step}.")

    cues = [pending[-1].content for _prompt, pending in podcast_client.writer.received]
    assert all(cue.startswith(PRODUCER_NOTE_MARKER) for cue in cues)
    assert any("to settle it" in cue for cue in cues)


def test_after_the_wrap_up_the_learner_can_still_talk_until_the_end(podcast_client):
    episode_id = podcast_client.start("panel")
    for step in range(40):
        _advance(podcast_client, episode_id, f"Respuesta {step}.")
        if any(line["intent"] == "wrap_up" for line in podcast_client.episode(episode_id)["lines"]):
            break
    for step in range(6):
        _advance(podcast_client, episode_id, f"Después {step}.")

    lines = podcast_client.episode(episode_id)["lines"]
    after_wrap = lines[[line["intent"] for line in lines].index("wrap_up") + 1 :]
    assert any(line["speaker"] == "learner" for line in after_wrap)
    assert any(line["speaker"] == "host" for line in after_wrap)
    assert podcast_client.episode(episode_id)["status"] == "active"
