"""T007: the podcast catalogues and their invariants (data-model §1.1–§1.4, §1.6 P1–P5)."""

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from app.podcasts import catalog as podcast_catalog
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
        podcast_format.has_pass,
        podcast_format.max_host_run,
        podcast_format.invite_deadline,
    )


def test_the_formats_are_one_host_panel_and_listen_in_order():
    assert list(PODCAST_FORMATS) == ["one_host", "panel", "listen"]


def test_the_format_descriptors_match_the_data_model():
    assert {key: _descriptor(value) for key, value in PODCAST_FORMATS.items()} == {
        # 011 research R15: One host gains Jump in; Pass stays Panel's only.
        "one_host": (1, True, True, False, None, 1),
        "panel": (2, True, True, True, 3, 4),
        "listen": (2, False, False, False, 3, None),
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


# --- 010: recurring shows (data-model §1) -------------------------------------------------

SHOW_IDS_BEFORE_010 = [
    "weekend-food-talk",
    "tech-for-normal-people",
    "game-day",
    "on-the-road",
    "screen-and-sound",
    "nine-to-five",
    "home-sweet-home",
    "big-little-questions",
]


def test_find_a_new_show_is_a_show_source():
    from app.podcasts.catalog import SHOW_SOURCES

    assert "suggested" in SHOW_SOURCES


def test_an_episode_is_a_one_off_or_part_of_a_series():
    from app.podcasts.catalog import EPISODE_KINDS

    assert EPISODE_KINDS == ("one_off", "series")


def test_the_memory_and_discovery_limits_match_the_data_model():
    from app.podcasts import catalog

    assert (
        catalog.MAX_REMEMBERED_TOPICS,
        catalog.MAX_REMEMBERED_ABOUT_LEARNER,
        catalog.MAX_POINTS_PER_EPISODE,
        catalog.REMEMBERED_POINT_MAX_LENGTH,
        catalog.REMEMBERED_TEXT_BUDGET,
        catalog.SERIES_SECTION_MAX_LENGTH,
        catalog.MIN_LINES_TO_REMEMBER,
        catalog.MEMORY_CHUNK_CHARACTERS,
        catalog.MEMORY_WAIT_SECONDS,
        catalog.SUGGESTION_SEEDS,
        catalog.MIN_SUGGESTIONS,
        catalog.INTEREST_SEEDS,
    ) == (10, 8, 3, 160, 1200, 1800, 2, 6000, 30, 5, 3, 3)


def test_the_ready_made_shows_are_unchanged_in_content_and_order():
    assert list(SHOW_TEMPLATES) == SHOW_IDS_BEFORE_010


# --- 011 T006: episode settings catalogues and constants (data-model §1.1–§1.4, §1.6) -------


EXPERT_CONFIGURED_STYLE = (
    "Explains how and why step by step, with simple facts and an everyday example, and stays "
    "precise."
)
INTERVIEWER_CONFIGURED_STYLE = (
    "Asks how and why, picks up details others said, and says what they think too."
)


def test_the_episode_styles_are_conversation_balanced_and_presented_in_order():
    styles = podcast_catalog.EPISODE_STYLES

    assert [(s.style_id, s.label, s.description, s.weights) for s in styles.values()] == [
        ("conversation", "Conversation", "Lots of back-and-forth.", (0.90, 0.07, 0.03)),
        ("balanced", "Balanced", "Some talk, some explaining.", (0.55, 0.30, 0.15)),
        (
            "presented",
            "Presented",
            "The hosts mostly explain and tell stories, like a radio show.",
            (0.35, 0.40, 0.25),
        ),
    ]
    assert list(styles) == ["conversation", "balanced", "presented"]
    assert podcast_catalog.DEFAULT_EPISODE_STYLE == "balanced"


def test_the_host_line_lengths_hold_their_counts_and_phrases():
    lengths = podcast_catalog.HOST_LINE_LENGTHS

    assert [
        (
            length.line_length_id,
            length.label,
            length.min_sentences,
            length.max_sentences,
            length.brief_phrase,
            length.full_phrase,
        )
        for length in lengths.values()
    ] == [
        ("short", "Short", 1, 2, "in one or two sentences", "in two sentences"),
        ("medium", "Medium", 3, 5, "in three sentences", "in four or five sentences"),
        ("long", "Long", 5, 8, "in five or six sentences", "in six to eight sentences"),
    ]
    assert podcast_catalog.DEFAULT_HOST_LINE_LENGTH == "medium"


@pytest.mark.parametrize(
    ("line_length_id", "phrase"),
    [
        ("short", "one to two sentences"),
        ("medium", "three to five sentences"),
        ("long", "five to eight sentences"),
    ],
)
def test_a_host_line_length_names_its_range(line_length_id, phrase):
    assert podcast_catalog.HOST_LINE_LENGTHS[line_length_id].range_phrase == phrase


def test_the_expert_and_the_interviewer_have_configured_speaking_styles():
    configured = {key: p.configured_speaking_style for key, p in PERSONALITIES.items()}

    assert configured.pop("expert") == EXPERT_CONFIGURED_STYLE
    assert configured.pop("curious_interviewer") == INTERVIEWER_CONFIGURED_STYLE
    assert set(configured.values()) == {None}


def test_the_legacy_speaking_styles_are_unchanged():
    assert PERSONALITIES["expert"].speaking_style == (
        "Gives one clear fact or tip at a time, explains simply, stays precise."
    )
    assert PERSONALITIES["curious_interviewer"].speaking_style == (
        "Asks follow-up questions, picks up details others said, digs gently."
    )


def test_the_invite_frequencies_hold_their_hazards():
    frequencies = podcast_catalog.INVITE_FREQUENCIES

    assert [(f.invite_frequency_id, f.label, f.hazards) for f in frequencies.values()] == [
        ("often", "Often", (1.0, 1.0, 1.0)),
        ("sometimes", "Sometimes", (0.35, 0.45, 0.55)),
        ("rarely", "Rarely", (0.0, 0.05, 0.10)),
    ]
    assert podcast_catalog.DEFAULT_INVITE_FREQUENCY == "sometimes"
    assert podcast_catalog.INVITE_DEADLINE == 4


@pytest.mark.parametrize(
    "catalogue_name", ["EPISODE_STYLES", "HOST_LINE_LENGTHS", "INVITE_FREQUENCIES"]
)
def test_every_episode_settings_catalogue_is_read_only(catalogue_name):
    assert isinstance(getattr(podcast_catalog, catalogue_name), MappingProxyType)


@pytest.mark.parametrize("weights", [(0.5, 0.5, 0.0), (0.6, 0.3, 0.3), (-0.1, 0.6, 0.5)], ids=str)
def test_a_style_needs_positive_weights_that_sum_to_one(weights):
    with pytest.raises(ValueError):
        podcast_catalog.EpisodeStyle("odd", "Odd", "Odd.", weights)


@pytest.mark.parametrize(("low", "high"), [(0, 2), (4, 3)])
def test_a_host_line_length_needs_one_or_more_sentences_in_order(low, high):
    with pytest.raises(ValueError):
        podcast_catalog.HostLineLength("odd", "Odd", low, high, "in a few", "in some")


@pytest.mark.parametrize("hazards", [(1.1, 0.5, 0.5), (0.2, -0.1, 0.5)], ids=str)
def test_an_invite_frequency_needs_hazards_between_zero_and_one(hazards):
    with pytest.raises(ValueError):
        podcast_catalog.InviteFrequency("odd", "Odd", hazards)


def test_the_011_constants_match_the_data_model():
    c = podcast_catalog

    assert c.TODAY_SUBJECT_MAX_LENGTH == 120
    assert c.SERIES_SETTING_NAMES == (
        "format",
        "length",
        "style",
        "line_length",
        "invite_frequency",
        "learner_role",
    )
    assert c.ANSWER_INTENTS == ("answer", "follow_up")
    assert c.DISCUSSION_INTENTS == ("react", "explain", "story")
    assert (c.QUESTION_MARK, c.MIN_SENTENCE_CHARACTERS) == ("?", 12)
    assert (c.PART_WAIT_SECONDS, c.PART_TTL_SECONDS) == (30, 600)
    assert c.ASKS == ("required", "allowed", "none", "never")
    assert c.ADDRESSEES == ("learner", "lead", "second")
    assert (c.ADDRESS_ALL, c.ADDRESS_TAG_MAX_LENGTH) == ("all", 60)
    assert c.BRIEF_INTENTS == ("greet", "react", "wrap_up", "sign_off")
    assert (c.SUBJECT_SUGGESTIONS, c.SUBJECT_AVOID_MAX) == (3, 10)


def test_every_new_intent_fits_the_host_line_intent_column():
    intents = podcast_catalog.ANSWER_INTENTS + podcast_catalog.DISCUSSION_INTENTS

    assert all(len(intent) <= 10 for intent in intents)


def test_every_ask_and_addressee_fits_its_column():
    values = podcast_catalog.ASKS + podcast_catalog.ADDRESSEES

    assert all(len(value) <= 8 for value in values)
