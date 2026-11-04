"""010 T013: the series value objects (data-model §3)."""

import json

import pytest

from app.podcasts.catalog import PODCAST_FORMATS
from app.podcasts.schemas import HostDraftModel, ShowDraftModel
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.library import ShowRef
from app.podcasts.services.series_snapshot import RememberedLine, SeriesBrief, SeriesSnapshot
from app.podcasts.services.series_storage import KeptShow, SeriesHost, SeriesRecord

HUGO = SeriesHost("lead", "Hugo", "curious_interviewer", "es_AR-daniela-high", "host", None, 0)
INES = SeriesHost("second", "Inés", "expert", "es_ES-davefx-medium", "co_host", "Facts.", 2)
SHOW = KeptShow(
    show_row_id=1,
    ref=ShowRef(template_id="big-little-questions"),
    source="ready_made",
    title="Big Little Questions",
    premise="Everyday curiosities.",
    topic="everyday curiosities",
    learner_role="guest",
    personalities=("curious_interviewer", "expert"),
    angles=(None, None),
    is_favourite=False,
    last_played_at=None,
)


def _draft(source: str = "ready_made", **changes) -> ShowDraftModel:
    hosts = [_host_draft(HUGO), _host_draft(INES)]
    values = {
        "source": source,
        "show_id": "big-little-questions" if source == "ready_made" else None,
        "title": "Big Little Questions",
        "premise": "Everyday curiosities.",
        "topic": "everyday curiosities",
        "learner_role": "guest",
        "language": "es",
        "hosts": hosts,
    }
    return ShowDraftModel(**{**values, **changes})


def _host_draft(host: SeriesHost, **changes) -> HostDraftModel:
    values = {
        "slot": host.slot,
        "name": host.name,
        "personality_id": host.personality_id,
        "voice_key": host.voice_key,
        "show_role": host.show_role,
        "angle": host.angle,
    }
    return HostDraftModel(**{**values, **changes})


def _series(count: int = 2) -> SeriesRecord:
    return SeriesRecord(1, SHOW, "es", (HUGO, INES), count, None)


# --- ShowRef ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "values", [{}, {"template_id": "game-day", "saved_show_id": 3}], ids=["none", "both"]
)
def test_a_show_ref_names_exactly_one_show(values):
    with pytest.raises(ValueError):
        ShowRef(**values)


def test_a_ready_made_draft_is_referred_to_by_its_template_id():
    assert ShowRef.of(_draft()) == ShowRef(template_id="big-little-questions")


def test_a_kept_learner_made_draft_is_referred_to_by_its_saved_id():
    assert ShowRef.of(_draft("generated", saved_show_id=7)) == ShowRef(saved_show_id=7)


def test_an_unsaved_learner_made_draft_has_no_ref():
    assert ShowRef.of(_draft("suggested")) is None


# --- SeriesHost ---------------------------------------------------------------------------


def test_a_series_host_becomes_the_episode_host():
    assert INES.to_host() == Host(
        "second", "Inés", "expert", "es_ES-davefx-medium", "co_host", "Facts."
    )


@pytest.mark.parametrize(("episode", "is_new"), [(1, False), (2, False), (3, True), (4, False)])
def test_a_host_is_new_in_the_episode_after_they_joined(episode, is_new):
    assert INES.is_new_in(episode) is is_new


def test_an_original_host_is_never_new():
    assert not any(HUGO.is_new_in(episode) for episode in range(1, 5))


@pytest.mark.parametrize(("count", "has_history"), [(2, False), (3, True)])
def test_a_host_has_history_once_an_episode_ran_with_them(count, has_history):
    assert INES.has_history(count) is has_history


# --- SeriesRecord -------------------------------------------------------------------------


def test_the_next_episode_follows_the_count():
    assert _series(count=4).next_episode_number == 5


def test_the_draft_hosts_match_the_series_hosts():
    assert _series().matches(_draft().hosts)


@pytest.mark.parametrize(
    "change",
    [
        {"name": "Pablo"},
        {"personality_id": "joker"},
        {"voice_key": "es_AR-daniela-high"},
    ],
    ids=["name", "personality", "voice"],
)
def test_any_changed_host_is_not_a_match(change):
    hosts = [_host_draft(HUGO), _host_draft(INES, **change)]

    assert not _series().matches(hosts)


def test_swapped_slots_are_not_a_match():
    hosts = [_host_draft(HUGO, slot="second"), _host_draft(INES, slot="lead")]

    assert not _series().matches(hosts)


# --- SeriesSnapshot -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "snapshot",
    [
        SeriesSnapshot(1),
        SeriesSnapshot(3, ("el sueño",), ("Odia las mañanas.",), ("second",)),
        SeriesSnapshot(
            12,
            tuple(f"tema «{n}» — ñ" for n in range(10)),
            tuple(f"Le encanta el café {n}." for n in range(8)),
            ("lead", "second"),
        ),
    ],
    ids=["empty", "typical", "full"],
)
def test_a_snapshot_round_trips_through_json(snapshot):
    assert SeriesSnapshot.from_json(snapshot.to_json()) == snapshot


def test_a_snapshot_keeps_non_ascii_text_readable():
    assert "mañanas" in SeriesSnapshot(2, (), ("Odia las mañanas.",)).to_json()


# --- SeriesBrief --------------------------------------------------------------------------


def test_the_brief_names_the_new_hosts_from_the_cast():
    cast = Cast.for_format(PODCAST_FORMATS["panel"], HUGO.to_host(), INES.to_host())

    brief = SeriesBrief.of(SeriesSnapshot(3, new_host_slots=("second",)), cast)

    assert brief.new_host_names == ("Inés",)
    assert brief.episode_number == 3


def test_a_new_host_who_is_not_in_the_episode_is_not_named():
    cast = Cast.for_format(PODCAST_FORMATS["one_host"], HUGO.to_host(), None)

    brief = SeriesBrief.of(SeriesSnapshot(3, new_host_slots=("second",)), cast)

    assert brief.new_host_names == ()
    assert not brief.is_new_host("second")


# --- 011 T091: a guest in the snapshot (data-model §2.5) ----------------------------------

_010_SNAPSHOT_JSON = (
    '{"episode_number": 4, "topics_covered": ["el sueño"], "about_learner": [], '
    '"new_host_slots": []}'
)


def test_a_snapshot_with_a_guest_round_trips_through_json():
    snapshot = SeriesSnapshot(4, ("el sueño",), guest_slot="second")

    assert SeriesSnapshot.from_json(snapshot.to_json()) == snapshot


def test_a_010_snapshot_loads_with_no_guest():
    assert SeriesSnapshot.from_json(_010_SNAPSHOT_JSON).guest_slot is None


def test_a_snapshot_with_no_guest_writes_010s_json_byte_for_byte():
    assert SeriesSnapshot(4, ("el sueño",)).to_json() == _010_SNAPSHOT_JSON


def test_the_brief_names_the_guest_from_the_cast():
    marco = Host("second", "Marco", "expert", "es_ES-davefx-medium", "co_host")
    cast = Cast.for_format(PODCAST_FORMATS["panel"], HUGO.to_host(), marco)

    brief = SeriesBrief.of(SeriesSnapshot(4, guest_slot="second"), cast)

    assert (brief.guest_slot, brief.guest_name) == ("second", "Marco")


def test_a_brief_without_a_guest_names_none():
    cast = Cast.for_format(PODCAST_FORMATS["one_host"], HUGO.to_host(), None)

    brief = SeriesBrief.of(SeriesSnapshot(4), cast)

    assert (brief.guest_slot, brief.guest_name) == (None, None)


# --- 011 T113: missed marks and the away host (data-model §2.5, §3.5) --------------------


def test_a_remembered_line_has_no_marks_by_default():
    assert RememberedLine("el sueño").missed_by == ()


def test_snapshot_points_are_remembered_lines_even_when_given_as_text():
    snapshot = SeriesSnapshot(4, ("el sueño",), ("Odia las mañanas.",))

    assert snapshot.topics_covered == (RememberedLine("el sueño"),)
    assert snapshot.about_learner == (RememberedLine("Odia las mañanas."),)


def test_a_marked_point_is_written_as_an_object_and_an_unmarked_one_as_text():
    snapshot = SeriesSnapshot(4, (RememberedLine("el sueño", ("second",)), "los bostezos"))

    stored = json.loads(snapshot.to_json())

    assert stored["topics_covered"] == [
        {"text": "el sueño", "missed_by": ["second"]},
        "los bostezos",
    ]


def test_both_point_forms_and_the_away_host_round_trip_through_json():
    snapshot = SeriesSnapshot(
        5,
        (RememberedLine("el sueño", ("second",)),),
        (RememberedLine("Odia las mañanas.", ("lead", "second")), "Va a la playa."),
        guest_slot="second",
        away_host_name="Clara",
    )

    assert SeriesSnapshot.from_json(snapshot.to_json()) == snapshot


def test_a_010_snapshot_loads_with_no_marks_and_no_away_host():
    snapshot = SeriesSnapshot.from_json(_010_SNAPSHOT_JSON)

    assert snapshot.topics_covered == (RememberedLine("el sueño"),)
    assert snapshot.away_host_name is None


def test_a_snapshot_without_an_away_host_writes_no_key_for_it():
    assert "away_host_name" not in SeriesSnapshot(4, guest_slot="second").to_json()


def test_the_brief_gives_the_away_host_and_names_who_missed_a_point():
    marco = Host("second", "Marco", "joker", "es_ES-davefx-medium", "co_host")
    cast = Cast.for_format(PODCAST_FORMATS["panel"], HUGO.to_host(), marco)
    line = RememberedLine("el sueño", ("lead", "second"))

    brief = SeriesBrief.of(SeriesSnapshot(4, (line,), away_host_name="Inés"), cast)

    assert brief.away_host_name == "Inés"
    assert brief.missed_names(line) == ("Hugo", "Marco")


def test_a_point_missed_by_a_host_outside_the_episode_names_nobody():
    cast = Cast.for_format(PODCAST_FORMATS["one_host"], HUGO.to_host(), None)
    line = RememberedLine("el sueño", ("second",))

    assert SeriesBrief.of(SeriesSnapshot(4, (line,)), cast).missed_names(line) == ()
