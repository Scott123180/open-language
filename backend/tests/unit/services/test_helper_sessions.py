"""Unit tests for HelperSessionStore — bounded, expiring expression-helper threads."""

from datetime import timedelta

import pytest

from app.services.helper_sessions import HelperSessionStore


@pytest.fixture()
def store():
    return HelperSessionStore(max_sessions=3, ttl=timedelta(hours=1))


class TestHistoryAccumulation:
    def test_unknown_session_starts_empty(self, store):
        assert store.get_history("never-seen") == []

    def test_appended_exchange_is_returned_in_order(self, store):
        store.append_exchange("s1", user_message="hello?", assistant_message="hola")

        history = store.get_history("s1")

        assert [(turn.role, turn.content) for turn in history] == [
            ("user", "hello?"),
            ("assistant", "hola"),
        ]

    def test_sessions_do_not_share_history(self, store):
        store.append_exchange("s1", user_message="hello?", assistant_message="hola")
        store.append_exchange("s2", user_message="goodbye?", assistant_message="adios")

        assert len(store.get_history("s1")) == 2
        assert [turn.content for turn in store.get_history("s2")] == ["goodbye?", "adios"]

    def test_returned_history_cannot_mutate_the_store(self, store):
        store.append_exchange("s1", user_message="hello?", assistant_message="hola")

        store.get_history("s1").clear()

        assert len(store.get_history("s1")) == 2


class TestBounding:
    def test_oldest_session_is_evicted_beyond_the_limit(self, store):
        for index in range(4):
            store.append_exchange(f"s{index}", user_message="q", assistant_message="a")

        assert store.get_history("s0") == []
        assert len(store.get_history("s3")) == 2

    def test_store_never_exceeds_max_sessions(self, store):
        for index in range(10):
            store.append_exchange(f"s{index}", user_message="q", assistant_message="a")

        assert len(store) == 3

    def test_recently_used_session_survives_eviction(self, store):
        for index in range(3):
            store.append_exchange(f"s{index}", user_message="q", assistant_message="a")

        store.get_history("s0")  # touch the oldest so it is no longer least-recently-used
        store.append_exchange("s3", user_message="q", assistant_message="a")

        assert len(store.get_history("s0")) == 2
        assert store.get_history("s1") == []


class TestExpiry:
    def test_expired_session_returns_empty_history(self):
        store = HelperSessionStore(max_sessions=10, ttl=timedelta(seconds=0))

        store.append_exchange("s1", user_message="q", assistant_message="a")

        assert store.get_history("s1") == []

    def test_expired_session_is_dropped_from_the_store(self):
        store = HelperSessionStore(max_sessions=10, ttl=timedelta(seconds=0))

        store.append_exchange("s1", user_message="q", assistant_message="a")
        store.append_exchange("s2", user_message="q", assistant_message="a")

        assert len(store) <= 1

    def test_unexpired_session_is_retained(self, store):
        store.append_exchange("s1", user_message="q", assistant_message="a")

        assert len(store.get_history("s1")) == 2


class TestClear:
    def test_clear_removes_every_session(self, store):
        store.append_exchange("s1", user_message="q", assistant_message="a")
        store.append_exchange("s2", user_message="q", assistant_message="a")

        store.clear()

        assert len(store) == 0
        assert store.get_history("s1") == []
