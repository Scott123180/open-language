"""010 T084: a one-off episode neither reads nor adds to its show's series (FR-007, US2)."""

from app.conversation_levels import ConversationLevel
from app.podcasts.models import (
    PodcastSeries,
    PodcastSeriesEpisode,
    PodcastSeriesHost,
    PodcastSeriesMemory,
)
from app.podcasts.prompts import build_standing_prompt
from app.podcasts.services.episodes import load_episode
from tests.support.podcast_harness import EPISODES, SERIES_SHOW, podcast_harness

SERIES = "/api/podcasts/series"
MEMORY = {
    "topic": {"conversation_language": "el sueño", "english": "Sleep"},
    "about_learner": [
        {"conversation_language": "Odia las mañanas.", "english": "You hate mornings."}
    ],
}
SERIES_TABLES = (PodcastSeries, PodcastSeriesHost, PodcastSeriesEpisode, PodcastSeriesMemory)


def _series_rows(harness) -> dict[str, list]:
    session = harness.session()
    return {
        table.__tablename__: [
            {column.name: getattr(row, column.name) for column in table.__table__.columns}
            for row in session.query(table).all()
        ]
        for table in SERIES_TABLES
    }


def _series_at_episode_two(harness) -> int:
    first = harness.start_series("one_host", learner_name="Sam")
    harness.stream(first["conversation_id"], "next")
    harness.say(first["conversation_id"], "Odio las mañanas.")
    harness.memory.queue(MEMORY)
    harness.stream(first["conversation_id"], "end")
    return first["series"]["series_id"]


def _one_off(harness, hosts=None) -> dict:
    show = harness.listing(SERIES_SHOW)
    if hosts is not None:
        show = {**show, "hosts": hosts}
    body = {
        "show": show,
        "format": "panel",
        "length": "short",
        "learner_name": "Sam",
        "kind": "one_off",
    }
    response = harness.client.post(EPISODES, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_a_one_off_writes_no_series_row_and_triggers_no_memory(tmp_path):
    with podcast_harness(tmp_path) as harness:
        series_id = _series_at_episode_two(harness)
        before, calls_before = _series_rows(harness), len(harness.memory.calls)
        detail_before = harness.client.get(f"{SERIES}/{series_id}").json()

        one_off = _one_off(harness)
        harness.play_through(one_off["conversation_id"])

        assert one_off["series"] is None
        assert _series_rows(harness) == before
        assert len(harness.memory.calls) == calls_before
        detail = harness.client.get(f"{SERIES}/{series_id}").json()
        assert detail["next_episode_number"] == detail_before["next_episode_number"] == 2
        assert detail["remembered"] == detail_before["remembered"]


def test_a_one_off_prompt_has_no_series_section(tmp_path):
    with podcast_harness(tmp_path) as harness:
        _series_at_episode_two(harness)
        one_off = _one_off(harness)
        harness.stream(one_off["conversation_id"], "next")

        standing_prompt, _pending = harness.writer.received[-1]
        episode = load_episode(harness.podcasts, one_off["conversation_id"])
        show = episode.standing_prompt(ConversationLevel.NATURAL)
        plain = build_standing_prompt(
            _brief(episode),
            episode.cast,
            episode.learner_label,
            episode.languages,
            ConversationLevel.NATURAL,
        )
        assert standing_prompt == show == plain
        assert (
            "continuing show" not in standing_prompt and "Odia las mañanas" not in standing_prompt
        )


def test_a_one_off_with_other_hosts_leaves_the_series_hosts_alone(tmp_path):
    with podcast_harness(tmp_path) as harness:
        series_id = _series_at_episode_two(harness)
        hosts_before = harness.client.get(f"{SERIES}/{series_id}").json()["hosts"]
        listing = harness.listing(SERIES_SHOW)
        shuffled = harness.client.post(
            "/api/podcasts/hosts/shuffle",
            json={
                "language": "es",
                "slot": "second",
                "hosts": listing["hosts"],
                "learner_name": "Sam",
            },
        ).json()

        one_off = _one_off(harness, hosts=[listing["hosts"][0], shuffled])

        assert one_off["hosts"][1]["name"] == shuffled["name"]
        assert harness.client.get(f"{SERIES}/{series_id}").json()["hosts"] == hosts_before


def _brief(episode):
    from app.podcasts.prompts import ShowBrief

    record = episode.record
    return ShowBrief(record.title, record.premise, record.topic, record.learner_role)
