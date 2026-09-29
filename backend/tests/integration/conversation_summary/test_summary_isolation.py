"""T082: reading a summary changes nothing in the conversation (FR-041)."""

from app.services.conversation import SessionKey, SessionKind
from app.services.factory import get_episode_locks
from tests.integration.conversation_summary.conftest import roleplay_with_lines, summary_of
from tests.support.podcast_harness import lines_of


def test_a_summary_adds_no_line_and_leaves_the_session_alone(summary_client):
    episode_id = summary_client.start("listen")
    summary_client.stream(episode_id, "next")
    summary_client.stream(episode_id, "next")
    key = SessionKey(SessionKind.PODCAST, str(episode_id))
    before = (
        len(summary_client.conversations.get_messages(episode_id)),
        len(summary_client.writer.received),
    )

    assert summary_of(summary_client, episode_id).status_code == 200

    after = (
        len(summary_client.conversations.get_messages(episode_id)),
        len(summary_client.writer.received),
    )
    assert after == before
    assert summary_client.engine.is_live(key)


def test_a_roleplay_summary_works(summary_client):
    conversation_id = roleplay_with_lines(summary_client, 4)

    assert summary_of(summary_client, conversation_id).json()["status"] == "ready"


def test_a_finished_episode_can_still_be_summarised(summary_client):
    episode_id = summary_client.start("one_host")
    summary_client.stream(episode_id, "next")
    summary_client.stream(episode_id, "end")

    assert summary_of(summary_client, episode_id).json()["status"] == "ready"


def test_an_episode_transcript_names_its_hosts(summary_client, summary_llm):
    episode_id = summary_client.start("panel", learner_name="Sam")
    [opening] = lines_of(summary_client.stream(episode_id, "next"))
    lead = summary_client.episode(episode_id)["hosts"][0]["name"]

    summary_client.stream(episode_id, "end")
    summary_of(summary_client, episode_id)

    assert f"{lead}: {opening['content']}" in summary_llm.last_prompt
    assert "Partner:" not in summary_llm.last_prompt


def test_a_summary_during_a_line_covers_the_saved_lines_and_keeps_the_lock(summary_client):
    episode_id = summary_client.start("listen")
    summary_client.stream(episode_id, "next")
    summary_client.stream(episode_id, "next")
    held = get_episode_locks().try_acquire(episode_id)

    try:
        response = summary_of(summary_client, episode_id)
        still_held = get_episode_locks().is_held(episode_id)
    finally:
        held.release()

    assert response.status_code == 200
    assert (
        response.json()["up_to_message_id"]
        == summary_client.conversations.get_messages(episode_id)[-1].id
    )
    assert still_held
