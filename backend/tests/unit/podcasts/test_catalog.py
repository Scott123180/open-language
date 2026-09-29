"""T007: the podcast catalogues and their invariants (data-model §1.1–§1.4, §1.6 P1–P5)."""

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from app.podcasts.catalog import (
    DEFAULT_EPISODE_LENGTH,
    DEFAULT_PODCAST_FORMAT,
    EPISODE_LENGTHS,
    LEARNER_ROLES,
    MAX_PARTICIPANTS,
    PERSONALITIES,
    PODCAST_FORMATS,
    PODCAST_SCENARIO_ID,
    SHOW_TEMPLATES,
)

PERSONALITY_IDS = [
    "enthusiast",
    "dry_sceptic",
    "storyteller",
    "curious_interviewer",
    "expert",
    "joker",
    "warm_mentor",
    "contrarian",
    "dreamer",
    "pragmatist",
]
CATALOGUES = [PODCAST_FORMATS, EPISODE_LENGTHS, PERSONALITIES, SHOW_TEMPLATES]


def _descriptor(podcast_format) -> tuple:
    return (
        podcast_format.host_count,
        podcast_format.is_learner_speaking,
        podcast_format.has_jump_in,
        podcast_format.max_host_run,
        podcast_format.invite_deadline,
    )


def test_the_formats_are_one_host_panel_and_listen_in_order():
    assert list(PODCAST_FORMATS) == ["one_host", "panel", "listen"]


def test_the_format_descriptors_match_the_data_model():
    assert {key: _descriptor(value) for key, value in PODCAST_FORMATS.items()} == {
        "one_host": (1, True, False, None, 1),
        "panel": (2, True, True, 3, 4),
        "listen": (2, False, False, 3, None),
    }


def test_the_format_labels_are_learner_facing():
    assert [f.label for f in PODCAST_FORMATS.values()] == ["One host", "Panel", "Listen"]


def test_the_default_format_is_one_host():
    assert DEFAULT_PODCAST_FORMAT == "one_host"


def test_the_lengths_are_short_medium_and_long():
    assert {key: value.target_host_lines for key, value in EPISODE_LENGTHS.items()} == {
        "short": 10,
        "medium": 20,
        "long": 40,
    }


def test_the_default_length_is_medium():
    assert DEFAULT_EPISODE_LENGTH == "medium"


def test_there_are_exactly_the_ten_personalities():
    assert list(PERSONALITIES) == PERSONALITY_IDS


@pytest.mark.parametrize("personality", PERSONALITIES.values(), ids=lambda p: p.personality_id)
def test_every_personality_is_described(personality):
    assert personality.label.strip()
    assert personality.description.strip()
    assert personality.speaking_style.strip()


def test_there_are_eight_ready_made_shows():
    assert len(SHOW_TEMPLATES) == 8


@pytest.mark.parametrize("show", SHOW_TEMPLATES.values(), ids=lambda s: s.show_id)
def test_every_show_has_a_known_learner_role(show):
    assert show.learner_role in {"guest", "co_host", "caller"}


@pytest.mark.parametrize("show", SHOW_TEMPLATES.values(), ids=lambda s: s.show_id)
def test_every_show_has_a_title_premise_and_topic(show):
    assert show.title.strip() and show.premise.strip() and show.topic.strip()


def test_the_learner_roles_are_guest_co_host_and_caller():
    assert LEARNER_ROLES == ("guest", "co_host", "caller")


def test_the_podcast_scenario_id_is_podcast():
    assert PODCAST_SCENARIO_ID == "podcast"


# --- invariants P1–P5 -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("catalogue", "id_field"),
    [
        (PODCAST_FORMATS, "format_id"),
        (EPISODE_LENGTHS, "length_id"),
        (PERSONALITIES, "personality_id"),
        (SHOW_TEMPLATES, "show_id"),
    ],
)
def test_p1_every_entry_is_keyed_by_its_own_unique_id(catalogue, id_field):
    ids = [getattr(entry, id_field) for entry in catalogue.values()]

    assert ids == list(catalogue)
    assert len(set(ids)) == len(ids)


def test_p2_there_are_enough_personalities_and_shows():
    assert len(PERSONALITIES) >= 8
    assert len(SHOW_TEMPLATES) >= 6


@pytest.mark.parametrize("show", SHOW_TEMPLATES.values(), ids=lambda s: s.show_id)
def test_p3_every_show_has_two_different_known_default_personalities(show):
    lead, second = show.default_personalities

    assert lead in PERSONALITIES and second in PERSONALITIES
    assert lead != second


@pytest.mark.parametrize("podcast_format", PODCAST_FORMATS.values(), ids=lambda f: f.format_id)
def test_p4_every_format_respects_the_participant_bound(podcast_format):
    learner = 1 if podcast_format.is_learner_speaking else 0

    assert podcast_format.host_count + learner <= MAX_PARTICIPANTS == 3


@pytest.mark.parametrize("podcast_format", PODCAST_FORMATS.values(), ids=lambda f: f.format_id)
def test_p4_the_run_cap_is_absent_exactly_with_one_host(podcast_format):
    assert (podcast_format.max_host_run is None) == (podcast_format.host_count == 1)


@pytest.mark.parametrize("podcast_format", PODCAST_FORMATS.values(), ids=lambda f: f.format_id)
def test_p4_the_invite_deadline_is_absent_exactly_when_the_learner_listens(podcast_format):
    assert (podcast_format.invite_deadline is None) == (not podcast_format.is_learner_speaking)


def test_p5_the_defaults_exist():
    assert DEFAULT_PODCAST_FORMAT in PODCAST_FORMATS
    assert DEFAULT_EPISODE_LENGTH in EPISODE_LENGTHS


@pytest.mark.parametrize("catalogue", CATALOGUES)
def test_every_catalogue_is_read_only(catalogue):
    assert isinstance(catalogue, MappingProxyType)


@pytest.mark.parametrize("catalogue", CATALOGUES)
def test_every_descriptor_is_frozen(catalogue):
    entry = next(iter(catalogue.values()))
    field = next(iter(entry.__dataclass_fields__))

    with pytest.raises(FrozenInstanceError):
        setattr(entry, field, "changed")
