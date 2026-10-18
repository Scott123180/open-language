"""010 T014: the new and extended request and response shapes (data-model §6, contracts §1–§4)."""

import pytest
from pydantic import ValidationError

from app.podcasts.schemas import (
    DiscoverRequest,
    EpisodeSummaryRow,
    RecastRequest,
    SeriesSummaryModel,
    ShowDraftModel,
    ShowListing,
    StartEpisodeRequest,
    UnfinishedEpisodeModel,
)

HOSTS = [
    {
        "slot": "lead",
        "name": "Hugo",
        "personality_id": "curious_interviewer",
        "voice_key": "es_AR-daniela-high",
        "show_role": "host",
        "angle": None,
    },
    {
        "slot": "second",
        "name": "Inés",
        "personality_id": "expert",
        "voice_key": "es_ES-davefx-medium",
        "show_role": "co_host",
        "angle": None,
    },
]
DRAFT = {
    "source": "ready_made",
    "show_id": "big-little-questions",
    "title": "Big Little Questions",
    "premise": "Everyday curiosities.",
    "topic": "everyday curiosities",
    "learner_role": "guest",
    "language": "es",
    "hosts": HOSTS,
}


def _start(**changes) -> StartEpisodeRequest:
    return StartEpisodeRequest(**{"show": DRAFT, "format": "panel", "length": "short", **changes})


def test_an_episode_is_a_one_off_unless_asked_otherwise():
    assert _start().kind == "one_off"
    assert _start(kind="series").kind == "series"


def test_an_unknown_episode_kind_is_refused():
    with pytest.raises(ValidationError):
        _start(kind="season")


def test_a_draft_has_no_saved_show_unless_given():
    assert ShowDraftModel(**DRAFT).saved_show_id is None


def test_a_suggested_show_is_an_accepted_source():
    assert ShowDraftModel(**{**DRAFT, "source": "suggested", "show_id": None}).source == "suggested"


def test_a_listing_posted_back_as_a_draft_is_accepted():
    unfinished = UnfinishedEpisodeModel(conversation_id=81, episode_number=1)
    series = SeriesSummaryModel(
        series_id=4, episode_count=1, next_episode_number=2, unfinished_episode=unfinished
    )
    listing = ShowListing(**DRAFT, is_favourite=True, series=series)

    request = _start(show=listing.model_dump(mode="json"))

    assert request.show == ShowDraftModel(**DRAFT)


def test_a_past_chats_row_has_no_episode_number_unless_given():
    row = EpisodeSummaryRow(
        conversation_id=1,
        show_title="Game Day",
        format="panel",
        format_label="Panel",
        host_names=["Jonas"],
        language="de",
        language_name="German",
        status="completed",
    )

    assert row.episode_number is None


@pytest.mark.parametrize("titles", [["Title"] * 51, ["x" * 201]], ids=["too-many", "too-long"])
def test_find_a_new_show_refuses_an_oversized_avoid_list(titles):
    with pytest.raises(ValidationError):
        DiscoverRequest(avoid_titles=titles)


def test_find_a_new_show_accepts_the_largest_avoid_list():
    assert len(DiscoverRequest(avoid_titles=["x" * 200] * 50).avoid_titles) == 50


def test_a_recast_may_leave_the_personality_to_chance():
    assert RecastRequest(language="es").personality_id is None
    assert RecastRequest(language="es", personality_id="joker").personality_id == "joker"
