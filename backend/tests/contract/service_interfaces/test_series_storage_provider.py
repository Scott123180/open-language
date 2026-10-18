"""010 T009: the show library, series and episode-endings interfaces (data-model §4, ISP)."""

import inspect
from abc import ABC

from app.podcasts.services.episode_endings import EpisodeEndings, NoEpisodeEndings
from app.podcasts.services.series_storage import SeriesStorage, ShowLibraryStorage
from app.podcasts.services.sqlite_series_storage import (
    SQLiteSeriesStorage,
    SQLiteShowLibraryStorage,
)
from app.podcasts.services.storage import PodcastStorage

LIBRARY_METHODS = {"keep", "get", "find", "set_favourite", "touch_played", "list_mine", "forget"}
SERIES_METHODS = {
    "find",
    "get",
    "create",
    "recast",
    "reset",
    "remembered",
    "pending_episodes",
    "remember",
}
PODCAST_METHODS_007 = {
    "create_episode",
    "get_episode",
    "list_episodes",
    "get_hosts",
    "save_host_line",
    "get_lines",
    "mark_passed",
    "mark_revealed",
    "get_preferences",
    "save_preferences",
}


def test_the_show_library_storage_is_an_abc_declaring_exactly_its_methods():
    assert issubclass(ShowLibraryStorage, ABC)
    assert ShowLibraryStorage.__abstractmethods__ == frozenset(LIBRARY_METHODS)


def test_the_series_storage_is_an_abc_declaring_exactly_its_methods():
    assert issubclass(SeriesStorage, ABC)
    assert SeriesStorage.__abstractmethods__ == frozenset(SERIES_METHODS)


def test_episode_endings_has_one_method_taking_the_conversation_id():
    assert issubclass(EpisodeEndings, ABC)
    assert EpisodeEndings.__abstractmethods__ == frozenset({"episode_finished"})
    parameters = inspect.signature(EpisodeEndings.episode_finished).parameters
    assert list(parameters) == ["self", "conversation_id"]


def test_the_sqlite_classes_implement_every_method():
    assert issubclass(SQLiteShowLibraryStorage, ShowLibraryStorage)
    assert issubclass(SQLiteSeriesStorage, SeriesStorage)
    assert not SQLiteShowLibraryStorage.__abstractmethods__
    assert not SQLiteSeriesStorage.__abstractmethods__


def test_the_null_endings_implement_the_interface_and_do_nothing():
    assert NoEpisodeEndings().episode_finished(1) is None


def test_the_podcast_storage_gains_no_method():
    assert PodcastStorage.__abstractmethods__ == frozenset(PODCAST_METHODS_007)
