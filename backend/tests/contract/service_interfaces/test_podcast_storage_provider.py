"""T009: PodcastStorage is an ABC, and the SQLite storage implements every method of it."""

from abc import ABC

from app.podcasts.services.sqlite_storage import SQLitePodcastStorage
from app.podcasts.services.storage import PodcastStorage

METHODS = {
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


def test_podcast_storage_is_an_abc_declaring_exactly_its_methods():
    assert issubclass(PodcastStorage, ABC)
    assert PodcastStorage.__abstractmethods__ == frozenset(METHODS)


def test_the_sqlite_storage_implements_every_method():
    assert issubclass(SQLitePodcastStorage, PodcastStorage)
    assert not SQLitePodcastStorage.__abstractmethods__
