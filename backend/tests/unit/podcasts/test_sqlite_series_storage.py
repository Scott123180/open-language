"""010 T011: the SQLite series storage (data-model §2.2–§2.5, §4)."""

from pathlib import Path

import pytest

from app.models.conversation import Conversation
from app.podcasts.catalog import (
    MAX_REMEMBERED_ABOUT_LEARNER,
    MAX_REMEMBERED_TOPICS,
    REMEMBERED_POINT_MAX_LENGTH,
    REMEMBERED_TEXT_BUDGET,
)
from app.podcasts.models import PodcastEpisode, PodcastSeriesEpisode, PodcastShow
from app.podcasts.services.series_storage import (
    EpisodeRef,
    SeriesAlreadyExists,
    SeriesHost,
    ShowContent,
)
from app.podcasts.services.sqlite_series_storage import (
    SQLiteSeriesStorage,
    SQLiteShowLibraryStorage,
)
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.support.scratch_database import make_session
from tests.support.series_records import (
    SERIES_HOSTS,
    TickingClock,
    add_host_lines,
    add_learner_lines,
    make_series,
    reply,
    series_episode,
)


@pytest.fixture
def session(tmp_path: Path):
    db_session = make_session(tmp_path / "series.db")
    yield db_session
    db_session.close()


@pytest.fixture
def storage(session) -> SQLiteSeriesStorage:
    return SQLiteSeriesStorage(session, clock=TickingClock())


@pytest.fixture
def series(session):
    return make_series(session)


def _refresh(storage, series):
    return storage.get(series.series_id)


def _texts(storage, series) -> list[tuple[str, str]]:
    return [(p.kind, p.conversation_language) for p in storage.remembered(series.series_id)]


# --- create, find, get --------------------------------------------------------------------


def test_creating_a_series_stores_both_hosts_as_original_hosts(storage, session):
    kept = SQLiteShowLibraryStorage(session).keep(ShowContent.ready_made("game-day"))

    created = storage.create(kept.show_row_id, "es", SERIES_HOSTS)

    assert created.hosts == SERIES_HOSTS
    assert all(host.joined_after_episodes == 0 for host in created.hosts)
    assert (created.language, created.episode_count, created.unfinished) == ("es", 0, None)


def test_a_second_series_for_the_same_show_and_language_is_rejected(storage, series):
    with pytest.raises(SeriesAlreadyExists):
        storage.create(series.show.show_row_id, "es", SERIES_HOSTS)


def test_the_same_show_can_have_a_series_in_another_language(storage, series):
    german = storage.create(series.show.show_row_id, "de", SERIES_HOSTS)

    assert german.series_id != series.series_id
    assert storage.find(series.show.show_row_id, "de") == german


def test_find_and_get_return_the_same_series(storage, series):
    assert storage.find(series.show.show_row_id, "es") == storage.get(series.series_id) == series


def test_an_unknown_series_is_none(storage, series):
    assert storage.get(999) is None
    assert storage.find(series.show.show_row_id, "it") is None


def test_the_episode_count_is_the_number_of_linked_episodes(storage, session, series):
    series_episode(session, series, 1)
    series_episode(session, series, 2)

    assert _refresh(storage, series).episode_count == 2
    assert _refresh(storage, series).next_episode_number == 3


def test_the_latest_active_episode_is_unfinished(storage, session, series):
    first = series_episode(session, series, 1)
    SQLiteStorageProvider(session).complete_conversation(first)
    second = series_episode(session, series, 2)

    assert _refresh(storage, series).unfinished == EpisodeRef(second, 2)


def test_a_finished_latest_episode_leaves_nothing_unfinished(storage, session, series):
    first = series_episode(session, series, 1)
    SQLiteStorageProvider(session).complete_conversation(first)

    assert _refresh(storage, series).unfinished is None


# --- recast and reset ---------------------------------------------------------------------


def test_recasting_replaces_one_slot_and_records_when_the_host_joined(storage, session, series):
    series_episode(session, series, 1)
    series_episode(session, series, 2)
    newcomer = SeriesHost("second", "Pablo", "joker", "es_ES-davefx-medium", "co_host", None, 0)

    recast = storage.recast(series.series_id, newcomer)

    assert recast.hosts[0] == SERIES_HOSTS[0]
    assert recast.hosts[1] == SeriesHost(
        "second", "Pablo", "joker", "es_ES-davefx-medium", "co_host", None, 2
    )
    assert recast.episode_count == 2


def test_resetting_deletes_the_series_and_keeps_the_episodes(storage, session, series):
    episode_id = series_episode(session, series, 1)
    add_host_lines(session, episode_id, "Hola.", "¿Qué tal?")
    storage.remember(series.series_id, episode_id, reply("el sueño", "Odia las mañanas."), None)

    assert storage.reset(series.series_id) is True

    session.expire_all()
    assert storage.get(series.series_id) is None
    assert session.query(PodcastSeriesEpisode).count() == 0
    assert session.get(PodcastEpisode, episode_id) is not None
    assert session.get(Conversation, episode_id) is not None


def test_resetting_an_unknown_series_is_false(storage):
    assert storage.reset(999) is False


def test_resetting_drops_a_ready_made_show_kept_only_by_its_series(storage, session, series):
    storage.reset(series.series_id)

    session.expire_all()
    assert session.query(PodcastShow).count() == 0


def test_resetting_keeps_a_favourite_show(storage, session, series):
    SQLiteShowLibraryStorage(session).set_favourite(series.show.show_row_id, True)

    storage.reset(series.series_id)

    session.expire_all()
    assert session.query(PodcastShow).count() == 1


# --- remember -----------------------------------------------------------------------------


def test_remembering_writes_the_topic_and_learner_points(storage, session, series):
    episode_id = series_episode(session, series, 1)
    last = add_host_lines(session, episode_id, "Hola.", "Adiós.")[-1]

    storage.remember(series.series_id, episode_id, reply("el sueño", "Odia las mañanas."), last)

    points = storage.remembered(series.series_id)
    assert [(p.kind, p.conversation_language, p.english, p.episode_number) for p in points] == [
        ("learner", "Odia las mañanas.", "EN Odia las mañanas.", 1),
        ("topic", "el sueño", "EN el sueño", 1),
    ]


def test_a_reread_episode_replaces_its_topic(storage, session, series):
    episode_id = series_episode(session, series, 1)

    storage.remember(series.series_id, episode_id, reply("el sueño"), None)
    storage.remember(series.series_id, episode_id, reply("los bostezos"), None)

    assert _texts(storage, series) == [("topic", "los bostezos")]


def test_remembering_moves_the_marker(storage, session, series):
    episode_id = series_episode(session, series, 1)
    last = add_host_lines(session, episode_id, "Hola.", "Adiós.")[-1]

    storage.remember(series.series_id, episode_id, reply(None), last)

    assert session.get(PodcastSeriesEpisode, episode_id).remembered_up_to_message_id == last


def _fill(text: str) -> str:
    return text.ljust(REMEMBERED_POINT_MAX_LENGTH, ".")


def test_the_caps_keep_the_newest_points_of_each_kind(storage, session, series):
    for number in range(1, MAX_REMEMBERED_TOPICS + 3):
        episode_id = series_episode(session, series, number)
        learner = [f"l{number}a", f"l{number}b"]
        storage.remember(series.series_id, episode_id, reply(f"t{number}", *learner), None)

    points = storage.remembered(series.series_id)
    topics = [p.conversation_language for p in points if p.kind == "topic"]
    learner = [p.conversation_language for p in points if p.kind == "learner"]
    assert topics == [f"t{n}" for n in range(12, 2, -1)]
    assert learner == ["l12b", "l12a", "l11b", "l11a", "l10b", "l10a", "l9b", "l9a"]
    assert len(learner) == MAX_REMEMBERED_ABOUT_LEARNER


def test_the_text_budget_drops_the_oldest_points_of_either_kind(storage, session, series):
    for number in range(1, 11):
        episode_id = series_episode(session, series, number)
        learner = [_fill(f"l{number}")] if number >= 3 else []
        storage.remember(series.series_id, episode_id, reply(_fill(f"t{number}"), *learner), None)

    kept = [text.rstrip(".") for _kind, text in _texts(storage, series)]
    assert kept == ["l10", "t10", "l9", "t9", "l8", "t8", "l7"]
    assert sum(len(text) for _kind, text in _texts(storage, series)) <= REMEMBERED_TEXT_BUDGET


def test_a_failed_write_changes_neither_points_nor_marker(storage, session, series, monkeypatch):
    episode_id = series_episode(session, series, 1)
    last = add_host_lines(session, episode_id, "Hola.", "Adiós.")[-1]

    def fail(*_args):
        raise RuntimeError("disk full")

    monkeypatch.setattr(storage, "_prune", fail)
    with pytest.raises(RuntimeError):
        storage.remember(series.series_id, episode_id, reply("el sueño", "Odia."), last)

    session.expire_all()
    assert storage.remembered(series.series_id) == ()
    assert session.get(PodcastSeriesEpisode, episode_id).remembered_up_to_message_id is None


# --- pending episodes ---------------------------------------------------------------------


def test_only_episodes_with_enough_unread_lines_are_pending(storage, session, series):
    quiet = series_episode(session, series, 1)
    add_host_lines(session, quiet, "Hola.")
    busy = series_episode(session, series, 2)
    add_host_lines(session, busy, "Hola.")
    add_learner_lines(session, busy, "Hola, soy Sam.")

    pending = storage.pending_episodes(series.series_id)

    assert [(p.conversation_id, p.episode_number) for p in pending] == [(busy, 2)]


def test_lines_before_the_marker_are_not_unread(storage, session, series):
    episode_id = series_episode(session, series, 1)
    last = add_host_lines(session, episode_id, "Hola.", "Adiós.")[-1]
    storage.remember(series.series_id, episode_id, reply(None), last)
    add_host_lines(session, episode_id, "Una más.")

    assert storage.pending_episodes(series.series_id) == ()

    add_learner_lines(session, episode_id, "Y otra.")
    (pending,) = storage.pending_episodes(series.series_id)
    assert pending.remembered_up_to_message_id == last


# --- an episode removed from Past Chats ----------------------------------------------------


def test_deleting_an_episode_forgets_its_points_and_lowers_the_count(storage, session, series):
    first = series_episode(session, series, 1)
    second = series_episode(session, series, 2)
    storage.remember(series.series_id, first, reply("el sueño", "Odia las mañanas."), None)
    storage.remember(series.series_id, second, reply("los bostezos"), None)

    session.query(Conversation).filter(Conversation.id == first).delete()
    session.commit()

    assert _texts(storage, series) == [("topic", "los bostezos")]
    assert _refresh(storage, series).episode_count == 1
