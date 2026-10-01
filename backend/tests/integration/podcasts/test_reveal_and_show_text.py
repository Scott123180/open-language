"""T067: revealing a Listen line and the Show text preference (FR-043, contracts §2, §8)."""

import pytest
from sqlalchemy.orm import sessionmaker

from app.podcasts.services.sqlite_storage import SQLitePodcastStorage
from tests.support.podcast_harness import EPISODES, lines_of


def _reveal(podcast_client, episode_id: int, message_id: int):
    return podcast_client.client.post(f"{EPISODES}/{episode_id}/lines/{message_id}/reveal")


def test_revealing_a_line_marks_it_revealed(podcast_client):
    episode_id = podcast_client.start("listen")
    [line] = lines_of(podcast_client.stream(episode_id, "next"))

    response = _reveal(podcast_client, episode_id, line["message_id"])

    assert response.status_code == 204
    assert podcast_client.episode(episode_id)["lines"][0]["is_revealed"] is True


def test_revealing_twice_is_harmless(podcast_client):
    episode_id = podcast_client.start("listen")
    [line] = lines_of(podcast_client.stream(episode_id, "next"))
    _reveal(podcast_client, episode_id, line["message_id"])

    assert _reveal(podcast_client, episode_id, line["message_id"]).status_code == 204


def test_a_learner_message_cannot_be_revealed(podcast_client):
    episode_id = podcast_client.start("one_host")
    podcast_client.stream(episode_id, "next")
    podcast_client.say(episode_id, "Hola")
    learner = podcast_client.episode(episode_id)["lines"][1]

    assert _reveal(podcast_client, episode_id, learner["message_id"]).status_code == 404


def test_another_episodes_line_cannot_be_revealed(podcast_client):
    first = podcast_client.start("listen")
    other = podcast_client.start("listen")
    [line] = lines_of(podcast_client.stream(other, "next"))

    assert _reveal(podcast_client, first, line["message_id"]).status_code == 404


def test_an_unknown_line_cannot_be_revealed(podcast_client):
    episode_id = podcast_client.start("listen")

    assert _reveal(podcast_client, episode_id, 999).status_code == 404


def test_show_text_is_remembered(podcast_client):
    podcast_client.client.put("/api/podcasts/preferences", json={"is_show_text_on": True})
    engine = podcast_client.sessions.kw["bind"]

    stored = SQLitePodcastStorage(sessionmaker(bind=engine)()).get_preferences()

    assert stored.is_show_text_on is True


# --- the voice notices (spec edge case "fewer than two voices") -------------------------

ONE_VOICE = {"es_AR-daniela-high"}


@pytest.mark.parametrize(
    ("installed", "shared", "unavailable"),
    [(None, False, False), (ONE_VOICE, True, False), (set(), False, True)],
    ids=["two-voices", "one-voice", "no-voice"],
)
def test_the_catalogue_says_how_many_voices_there_are(tmp_path, installed, shared, unavailable):
    from tests.support.podcast_harness import podcast_harness

    with podcast_harness(tmp_path, installed=installed) as harness:
        voices = harness.client.get("/api/podcasts/catalog").json()["voices"]

    assert (voices["shared_voice_notice"] is not None) is shared
    assert (voices["unavailable_message"] is not None) is unavailable
    if shared:
        assert "share" in voices["shared_voice_notice"]


def test_a_listen_episode_with_one_voice_carries_the_shared_notice(tmp_path):
    from tests.support.podcast_harness import podcast_harness

    with podcast_harness(tmp_path, installed=ONE_VOICE) as harness:
        catalog = harness.client.get("/api/podcasts/catalog").json()
        episode_id = harness.start("listen")
        episode = harness.episode(episode_id)

    lead, second = catalog["shows"][0]["hosts"]
    assert lead["voice_key"] == second["voice_key"]
    assert episode["shared_voice_notice"] == catalog["voices"]["shared_voice_notice"]


def test_a_one_host_episode_has_no_shared_notice(tmp_path):
    from tests.support.podcast_harness import podcast_harness

    with podcast_harness(tmp_path, installed=ONE_VOICE) as harness:
        episode = harness.episode(harness.start("one_host"))

    assert episode["shared_voice_notice"] is None
