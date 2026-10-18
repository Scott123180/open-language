"""010 T032: preparing a series start (data-model §5.2, research R2, R5)."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from app.podcasts.services.series import (
    SeriesHostsChanged,
    SeriesService,
    StartRefused,
)

from app.podcasts.schemas import LANGUAGE_CHANGED, StartEpisodeRequest
from app.podcasts.services.library import ShowLibrary, ShowNoLongerKept
from app.podcasts.services.series_snapshot import SeriesSnapshot
from app.podcasts.services.series_storage import SeriesHost, ShowContent
from app.podcasts.services.storage import NewHost
from app.services.storage.base import AppSettingsRecord
from tests.support.fake_series_storage import FakeSeriesStorage, FakeShowLibraryStorage

HUGO = SeriesHost("lead", "Hugo", "curious_interviewer", "es_AR-daniela-high", "host", None, 0)
INES = SeriesHost("second", "Inés", "expert", "es_ES-davefx-medium", "co_host", None, 0)
GERMAN_HOSTS = (
    SeriesHost("lead", "Jonas", "curious_interviewer", "de_DE-thorsten-medium", "host", None, 0),
    SeriesHost("second", "Lea", "expert", "de_DE-kerstin-low", "co_host", None, 0),
)
TEMPLATE_ID = "big-little-questions"


def _settings(language: str = "es") -> AppSettingsRecord:
    return AppSettingsRecord(
        llm_model="llama3.1:8b",
        target_language=language,
        native_language="en",
        suggestion_count=2,
        whisper_model="small",
        updated_at=datetime(2026, 10, 17, tzinfo=UTC),
    )


def _host_draft(host: SeriesHost, **changes) -> dict:
    values = {
        "slot": host.slot,
        "name": host.name,
        "personality_id": host.personality_id,
        "voice_key": host.voice_key,
        "show_role": host.show_role,
        "angle": host.angle,
    }
    return {**values, **changes}


def _request(
    hosts=(HUGO, INES), source="ready_made", format="panel", kind="series", **show_changes
) -> StartEpisodeRequest:
    show = {
        "source": source,
        "show_id": TEMPLATE_ID if source == "ready_made" else None,
        "title": "Big Little Questions",
        "premise": "Everyday curiosities.",
        "topic": "everyday curiosities",
        "learner_role": "guest",
        "language": "es",
        "hosts": [_host_draft(host) for host in hosts],
        **show_changes,
    }
    return StartEpisodeRequest(show=show, format=format, length="short", kind=kind)


class World:
    def __init__(self, installed: int = 2) -> None:
        self.library_storage = FakeShowLibraryStorage()
        self.series_storage = FakeSeriesStorage(self.library_storage)
        self.service = SeriesService(
            ShowLibrary(self.library_storage), self.series_storage, lambda _language: installed
        )

    def existing_series(self, hosts=(HUGO, INES), episodes: int = 1, language: str = "es"):
        kept = self.library_storage.keep(ShowContent.ready_made(TEMPLATE_ID))
        return self.series_storage.add(kept, language, hosts, episode_count=episodes)


@pytest.fixture
def world() -> World:
    return World()


# --- the first episode creates the series --------------------------------------------------


def test_the_first_series_start_creates_the_series_from_the_draft_hosts(world):
    prepared = world.service.prepare(_request(), _settings())

    (series,) = world.series_storage.series.values()
    assert series.hosts == (HUGO, INES)
    assert prepared.series.series_id == series.series_id
    assert prepared.series.episode_number == 1
    assert prepared.series.snapshot == SeriesSnapshot(1)


def test_the_first_episode_is_checked_with_007s_rules(world):
    clashing = (HUGO, replace(INES, personality_id=HUGO.personality_id))

    with pytest.raises(StartRefused, match="different personalities"):
        world.service.prepare(_request(hosts=clashing), _settings())

    assert world.series_storage.series == {}


# --- later episodes ------------------------------------------------------------------------


def test_a_matching_start_is_the_next_episode_with_a_snapshot_of_memory(world):
    series = world.existing_series(episodes=2)
    world.series_storage.add_point(series.series_id, "topic", "el sueño", 1)
    world.series_storage.add_point(series.series_id, "learner", "Odia las mañanas.", 1)
    world.series_storage.add_point(series.series_id, "topic", "los bostezos", 2)

    prepared = world.service.prepare(_request(), _settings())

    assert prepared.series.episode_number == 3
    assert prepared.series.snapshot == SeriesSnapshot(
        3, ("los bostezos", "el sueño"), ("Odia las mañanas.",), ()
    )


@pytest.mark.parametrize(
    ("format", "slots"),
    [("one_host", ["lead"]), ("panel", ["lead", "second"]), ("listen", ["lead", "second"])],
)
def test_the_participating_hosts_are_the_series_hosts_for_the_format(world, format, slots):
    world.existing_series()

    prepared = world.service.prepare(_request(format=format), _settings())

    assert [host.slot for host in prepared.hosts] == slots
    assert prepared.hosts[0] == NewHost(
        "lead", "Hugo", "curious_interviewer", "es_AR-daniela-high", "host", None
    )


@pytest.mark.parametrize(
    "change",
    [{"name": "Pablo"}, {"personality_id": "joker"}, {"voice_key": "es_AR-daniela-high"}],
    ids=["name", "personality", "voice"],
)
def test_changed_hosts_are_refused_and_nothing_is_written(world, change):
    world.existing_series()
    changed = replace(INES, **change)

    with pytest.raises(SeriesHostsChanged):
        world.service.prepare(_request(hosts=(HUGO, changed)), _settings())

    assert world.library_storage.played == []
    assert len(world.series_storage.series) == 1


def test_a_series_whose_hosts_share_a_voice_still_starts_with_two_voices_installed(world):
    shared = replace(INES, voice_key=HUGO.voice_key)
    world.existing_series(hosts=(HUGO, shared))

    prepared = world.service.prepare(_request(hosts=(HUGO, shared)), _settings())

    assert prepared.series.episode_number == 2


def test_a_series_host_whose_voice_is_missing_still_starts():
    world = World(installed=0)
    world.existing_series()

    assert world.service.prepare(_request(), _settings()).series.episode_number == 2


def test_a_recast_host_is_new_in_the_next_episode(world):
    newcomer = SeriesHost("second", "Pablo", "joker", "es_ES-davefx-medium", "co_host", None, 2)
    world.existing_series(hosts=(HUGO, newcomer), episodes=2)

    prepared = world.service.prepare(_request(hosts=(HUGO, newcomer)), _settings())

    assert prepared.series.snapshot.new_host_slots == ("second",)


# --- keeping the show ----------------------------------------------------------------------


def test_a_ready_made_show_is_kept_and_played(world):
    prepared = world.service.prepare(_request(), _settings())

    (show,) = world.library_storage.shows.values()
    assert show.ref.template_id == TEMPLATE_ID
    assert world.library_storage.played == [show.show_row_id]
    assert prepared.saved_show_id is None


@pytest.mark.parametrize("source", ["generated", "surprise", "suggested"])
def test_a_learner_made_show_is_kept_and_played_with_its_saved_id(world, source):
    prepared = world.service.prepare(_request(source=source), _settings())

    (show,) = world.library_storage.shows.values()
    assert world.library_storage.played == [show.show_row_id]
    assert prepared.saved_show_id == show.show_row_id


def test_a_kept_learner_made_show_continues_its_series(world):
    first = world.service.prepare(_request(source="generated"), _settings())
    series_id = first.series.series_id
    stored = world.series_storage.series
    stored[series_id] = replace(stored[series_id], episode_count=1)

    second = world.service.prepare(
        _request(source="generated", saved_show_id=first.saved_show_id), _settings()
    )

    assert second.series.series_id == first.series.series_id
    assert second.series.episode_number == 2


def test_an_unknown_saved_show_is_refused(world):
    with pytest.raises(ShowNoLongerKept):
        world.service.prepare(_request(source="generated", saved_show_id=42), _settings())


# --- the language ----------------------------------------------------------------------------


def test_the_series_is_in_the_settings_language(world):
    request = _request(hosts=GERMAN_HOSTS, language="de")

    world.service.prepare(request, _settings("de"))

    (series,) = world.series_storage.series.values()
    assert series.language == "de"


def test_a_draft_in_another_language_is_refused(world):
    with pytest.raises(StartRefused, match=LANGUAGE_CHANGED):
        world.service.prepare(_request(), _settings("de"))


# --- the episode it creates ------------------------------------------------------------------


def test_the_new_episode_carries_the_series_link_and_hosts(world):
    prepared = world.service.prepare(_request(format="one_host"), _settings())

    episode = world.service.new_episode(prepared, _settings())

    assert episode.series == prepared.series
    assert episode.hosts == prepared.hosts
    assert (episode.show_source, episode.show_id, episode.format) == (
        "ready_made",
        TEMPLATE_ID,
        "one_host",
    )
    assert (episode.target_language, episode.native_language) == ("es", "en")
