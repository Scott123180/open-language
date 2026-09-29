"""T043: an episode is saved as it happens and resumed intact (FR-009, FR-032, US1-6)."""

from sqlalchemy.orm import sessionmaker

from tests.support.podcast_harness import EPISODES, serve_sessions


def test_the_hosts_are_identical_after_a_restart(podcast_client):
    episode_id = podcast_client.start("panel")
    before = podcast_client.episode(episode_id)["hosts"]
    engine = podcast_client.sessions.kw["bind"]
    serve_sessions(sessionmaker(bind=engine), [])
    podcast_client.engine.close()

    after = podcast_client.episode(episode_id)["hosts"]

    assert after == before
    assert [(h["name"], h["voice_key"]) for h in after] == [
        (h["name"], h["voice_key"]) for h in before
    ]


def test_lines_are_the_conversations_messages_in_order(podcast_client):
    episode_id = podcast_client.start("one_host")
    podcast_client.stream(episode_id, "next")
    podcast_client.say(episode_id, "Hola")

    lines = podcast_client.episode(episode_id)["lines"]
    messages = podcast_client.conversations.get_messages(episode_id)

    assert [line["message_id"] for line in lines] == [message.id for message in messages]
    assert [line["speaker"] for line in lines] == ["host", "learner", "host"]
    assert all((line["speaker"] == "host") == (line["host_id"] is not None) for line in lines)


def test_the_episode_is_listed_for_past_chats(podcast_client):
    episode_id = podcast_client.start("panel")

    [row] = podcast_client.client.get(EPISODES).json()

    lead, second = podcast_client.episode(episode_id)["hosts"]
    assert row == {
        "conversation_id": episode_id,
        "show_title": "Weekend Food Talk",
        "format": "panel",
        "format_label": "Panel",
        "host_names": [lead["name"], second["name"]],
        "language": "es",
        "language_name": "Spanish",
        "status": "active",
    }


def test_a_roleplay_conversation_is_not_an_episode(podcast_client):
    roleplay = podcast_client.client.post(
        "/api/conversations", json={"scenario_id": "buy-train-ticket"}
    ).json()

    response = podcast_client.client.get(f"{EPISODES}/{roleplay['id']}")

    assert (response.status_code, response.json()) == (404, {"detail": "Episode not found"})
    assert podcast_client.client.get(EPISODES).json() == []
