"""T044: episodes use the conversation engine's sessions (contracts §7, research R3)."""

from app.podcasts.prompts import PRODUCER_NOTE_MARKER
from app.services.conversation import SessionKey, SessionKind
from tests.integration.conversation_levels.level_harness import wait_until
from tests.support.podcast_harness import EPISODES, lines_of


def _two_lines(podcast_client) -> int:
    episode_id = podcast_client.start("listen")
    podcast_client.stream(episode_id, "next")
    podcast_client.stream(episode_id, "next")
    return episode_id


def test_consecutive_lines_reuse_one_session(podcast_client):
    _two_lines(podcast_client)

    assert podcast_client.writer.open_count == 1


def test_each_line_is_asked_for_with_one_fresh_cue(podcast_client):
    _two_lines(podcast_client)

    _prompt, pending = podcast_client.writer.received[-1]
    assert [turn.turn_id for turn in pending] == ["c1"]
    assert pending[0].content.startswith(PRODUCER_NOTE_MARKER)


def test_a_trimmed_line_ends_the_session_and_the_next_rebuilds_from_storage(podcast_client):
    episode_id = podcast_client.start("listen")
    second = podcast_client.episode(episode_id)["hosts"][1]["name"]
    podcast_client.writer.script(f"¡Hola a todos! {second}: ¡Hola!", "¿Qué tal?")
    [opening] = lines_of(podcast_client.stream(episode_id, "next"))

    podcast_client.stream(episode_id, "next")

    assert opening["content"] == "¡Hola a todos!"
    assert podcast_client.writer.open_count == 2
    rebuilt = podcast_client.writer.sessions[-1]
    assert list(rebuilt.synced_turn_ids)[:2] == ["c0", f"p{opening['message_id']}"]


def test_a_rebuilt_history_re_renders_every_cue(podcast_client):
    episode_id = _two_lines(podcast_client)
    first_cue = podcast_client.writer.received[0][1][0]
    podcast_client.engine.end(SessionKey(SessionKind.PODCAST, str(episode_id)))

    podcast_client.stream(episode_id, "next")

    rebuilt = podcast_client.writer.sessions[-1]
    assert rebuilt.history[0] == first_cue
    assert [turn.turn_id for turn in rebuilt.history] == ["c0", "p1", "c1", "p2"]
    assert podcast_client.writer.received[-1][1][-1].turn_id == "c2"


def test_a_level_change_rebuilds_with_the_new_levels_rules(podcast_client):
    episode_id = podcast_client.start("listen")
    podcast_client.stream(episode_id, "next")
    podcast_client.client.put("/api/settings", json={"conversation_level": "beginner"})

    podcast_client.stream(episode_id, "next")

    prompt, _pending = podcast_client.writer.received[-1]
    assert podcast_client.writer.open_count == 2
    assert prompt.rstrip().endswith("make that reply even simpler.")


def test_warming_uses_a_podcast_session(podcast_client):
    episode_id = podcast_client.start("listen")

    response = podcast_client.client.post(f"{EPISODES}/{episode_id}/session")

    assert response.status_code == 202
    assert response.json()["status"] in {"warming", "live"}
    key = SessionKey(SessionKind.PODCAST, str(episode_id))
    wait_until(lambda: podcast_client.engine.is_live(key))


def test_a_live_session_is_reported_live(podcast_client):
    episode_id = _two_lines(podcast_client)

    response = podcast_client.client.post(f"{EPISODES}/{episode_id}/session")

    assert response.json() == {"status": "live"}


def test_changing_the_practice_language_leaves_the_episode_alone(podcast_client):
    episode_id = podcast_client.start("listen")
    before = podcast_client.episode(episode_id)
    podcast_client.stream(episode_id, "next")
    prompt_before = podcast_client.writer.received[-1][0]
    podcast_client.client.put("/api/settings", json={"target_language": "de"})

    podcast_client.stream(episode_id, "next")

    after = podcast_client.episode(episode_id)
    assert (after["language"], after["hosts"]) == ("es", before["hosts"])
    assert podcast_client.writer.received[-1][0] == prompt_before
    assert podcast_client.writer.open_count == 1
