"""010 T010: the SQLite show library (data-model §2.1, §4, §5.1, research R9)."""

from pathlib import Path

import pytest

from app.podcasts.catalog import SHOW_TEMPLATES
from app.podcasts.models import PodcastEpisode, PodcastShow
from app.podcasts.services.series_storage import ShowContent, ShowRef
from app.podcasts.services.sqlite_series_storage import (
    SQLiteSeriesStorage,
    SQLiteShowLibraryStorage,
)
from tests.support.scratch_database import make_session
from tests.support.series_records import SERIES_HOSTS as HOSTS
from tests.support.series_records import TickingClock, series_episode

TEMPLATE_ID = "big-little-questions"
READY = ShowContent.ready_made(TEMPLATE_ID)
MADE = ShowContent(
    source="generated",
    template_id=None,
    title="Night Shift Abroad",
    premise="Two nurses swap stories about working far from home.",
    topic="living abroad as a nurse",
    learner_role="caller",
    personalities=("storyteller", "dry_sceptic"),
    angles=("Misses her home town.", None),
)


@pytest.fixture
def session(tmp_path: Path):
    db_session = make_session(tmp_path / "library.db")
    yield db_session
    db_session.close()


@pytest.fixture
def library(session) -> SQLiteShowLibraryStorage:
    return SQLiteShowLibraryStorage(session, clock=TickingClock())


@pytest.fixture
def series(session) -> SQLiteSeriesStorage:
    return SQLiteSeriesStorage(session)


def _rows(session) -> list[PodcastShow]:
    session.expire_all()
    return session.query(PodcastShow).order_by(PodcastShow.id).all()


def _made(**changes) -> ShowContent:
    values = {field: getattr(MADE, field) for field in MADE.__dataclass_fields__}
    return ShowContent(**{**values, **changes})


# --- keep --------------------------------------------------------------------------------


def test_keeping_a_ready_made_show_stores_only_its_template_id(library, session):
    library.keep(READY)

    (row,) = _rows(session)
    assert (row.template_id, row.source) == (TEMPLATE_ID, "ready_made")
    assert (row.title, row.premise, row.topic, row.learner_role) == (None, None, None, None)
    assert (row.lead_personality, row.second_personality) == (None, None)
    assert (row.lead_angle, row.second_angle) == (None, None)


def test_keeping_a_ready_made_show_twice_returns_the_same_row(library, session):
    first = library.keep(READY)
    second = library.keep(READY)

    assert first.show_row_id == second.show_row_id
    assert len(_rows(session)) == 1


@pytest.mark.parametrize("source", ["generated", "surprise", "suggested"])
def test_keeping_a_learner_made_show_stores_its_content(library, session, source):
    library.keep(_made(source=source))

    (row,) = _rows(session)
    assert (row.template_id, row.source, row.title) == (None, source, MADE.title)
    assert (row.premise, row.topic, row.learner_role) == (MADE.premise, MADE.topic, "caller")
    assert (row.lead_personality, row.second_personality) == MADE.personalities
    assert (row.lead_angle, row.second_angle) == MADE.angles


def test_keeping_the_same_learner_made_content_twice_returns_the_same_row(library, session):
    first = library.keep(MADE)
    second = library.keep(MADE)

    assert first.show_row_id == second.show_row_id
    assert len(_rows(session)) == 1


def test_a_kept_learner_made_show_is_referred_to_by_its_saved_id(library):
    kept = library.keep(MADE)

    assert kept.ref == ShowRef(saved_show_id=kept.show_row_id)
    assert (kept.title, kept.personalities, kept.angles) == (
        MADE.title,
        MADE.personalities,
        MADE.angles,
    )


# --- get ---------------------------------------------------------------------------------


def test_a_ready_made_show_reads_its_content_from_the_catalogue(library):
    library.keep(READY)

    kept = library.get(ShowRef(template_id=TEMPLATE_ID))

    template = SHOW_TEMPLATES[TEMPLATE_ID]
    assert kept.ref == ShowRef(template_id=TEMPLATE_ID)
    assert (kept.title, kept.premise, kept.topic) == (
        template.title,
        template.premise,
        template.topic,
    )
    assert (kept.learner_role, kept.personalities) == (
        template.learner_role,
        template.default_personalities,
    )
    assert kept.angles == (None, None)


def test_a_learner_made_show_is_found_by_its_saved_id(library):
    kept = library.keep(MADE)

    assert library.get(ShowRef(saved_show_id=kept.show_row_id)) == kept


@pytest.mark.parametrize(
    "ref", [ShowRef(template_id=TEMPLATE_ID), ShowRef(saved_show_id=99)], ids=["ready", "saved"]
)
def test_an_unknown_show_is_none(library, ref):
    assert library.get(ref) is None


# --- favourites and the row's lifetime ----------------------------------------------------


def test_favouriting_sets_the_time(library):
    kept = library.keep(READY)

    favourite = library.set_favourite(kept.show_row_id, True)

    assert favourite.is_favourite
    assert library.get(kept.ref).is_favourite


def test_unfavouriting_a_ready_made_show_without_a_series_deletes_its_row(library, session):
    kept = library.keep(READY)
    library.set_favourite(kept.show_row_id, True)

    assert library.set_favourite(kept.show_row_id, False) is None
    assert _rows(session) == []


def test_unfavouriting_an_unplayed_learner_made_show_without_a_series_deletes_it(library, session):
    kept = library.keep(MADE)
    library.set_favourite(kept.show_row_id, True)

    assert library.set_favourite(kept.show_row_id, False) is None
    assert _rows(session) == []


def test_unfavouriting_a_show_with_a_series_keeps_it(library, series):
    kept = library.keep(READY)
    library.set_favourite(kept.show_row_id, True)
    series.create(kept.show_row_id, "de", HOSTS)

    unfavourited = library.set_favourite(kept.show_row_id, False)

    assert unfavourited is not None and not unfavourited.is_favourite


def test_unfavouriting_a_played_learner_made_show_keeps_it(library):
    kept = library.keep(MADE)
    library.touch_played(kept.show_row_id)
    library.set_favourite(kept.show_row_id, True)

    unfavourited = library.set_favourite(kept.show_row_id, False)

    assert unfavourited is not None and not unfavourited.is_favourite


def test_touching_a_show_records_when_it_was_played(library):
    kept = library.keep(MADE)

    library.touch_played(kept.show_row_id)

    assert library.get(kept.ref).last_played_at is not None


# --- my shows (research R9) ----------------------------------------------------------------


def _titles(entries) -> list[str]:
    return [entry.show.title for entry in entries]


def test_my_shows_holds_favourites_series_and_played_learner_made_shows_newest_first(
    library, series
):
    ready = library.keep(READY)
    series.create(ready.show_row_id, "es", HOSTS)
    library.touch_played(ready.show_row_id)
    played = library.keep(MADE)
    library.touch_played(played.show_row_id)
    favourite = library.keep(ShowContent.ready_made("game-day"))
    library.set_favourite(favourite.show_row_id, True)
    library.keep(_made(title="Never Played"))

    entries = library.list_mine("es")

    assert _titles(entries) == ["Game Day", MADE.title, "Big Little Questions"]
    assert entries[2].series is not None and entries[2].series.language == "es"
    assert entries[0].series is None


def test_a_series_in_another_language_only_does_not_list_the_show(library, series):
    kept = library.keep(READY)
    series.create(kept.show_row_id, "de", HOSTS)

    assert library.list_mine("es") == []


def test_a_favourite_lists_the_show_in_every_language(library, series):
    kept = library.keep(READY)
    series.create(kept.show_row_id, "de", HOSTS)
    library.set_favourite(kept.show_row_id, True)

    (entry,) = library.list_mine("es")

    assert entry.show.is_favourite and entry.series is None


# --- forget (FR-024) ----------------------------------------------------------------------


def test_forgetting_a_learner_made_show_deletes_it_and_its_series(library, series, session):
    kept = library.keep(MADE)
    library.touch_played(kept.show_row_id)
    spanish = series.create(kept.show_row_id, "es", HOSTS)
    series.create(kept.show_row_id, "de", HOSTS)
    episode_id = series_episode(session, spanish)

    assert library.forget(kept.show_row_id) is True

    assert _rows(session) == []
    assert series.get(spanish.series_id) is None
    assert session.get(PodcastEpisode, episode_id) is not None


def test_forgetting_an_unknown_or_ready_made_show_is_false(library):
    ready = library.keep(READY)

    assert library.forget(999) is False
    assert library.forget(ready.show_row_id) is False
