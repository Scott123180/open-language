"""T106: interests are only ever what the learner typed (FR-023: never inferred)."""

from tests.support.podcast_harness import post_stream

PREFERENCES = "/api/podcasts/preferences"


def _interests(podcast_client) -> list[str]:
    return podcast_client.client.get(PREFERENCES).json()["interests"]


def test_a_roleplay_conversation_leaves_the_interests_unchanged(podcast_client):
    client = podcast_client.client
    client.put(PREFERENCES, json={"interests": ["chess"]})
    conversation = client.post(
        "/api/conversations", json={"scenario_id": "order-at-restaurant"}
    ).json()

    post_stream(
        client, f"/api/chat/{conversation['id']}/message", {"content": "Me encanta el fútbol."}
    )

    assert _interests(podcast_client) == ["chess"]


def test_a_saved_word_leaves_the_interests_unchanged(podcast_client):
    podcast_client.client.put(PREFERENCES, json={"interests": ["chess"]})

    response = podcast_client.client.post(
        "/api/vocabulary", json={"word": "el fútbol", "translation": "football"}
    )

    assert response.status_code == 201
    assert _interests(podcast_client) == ["chess"]
