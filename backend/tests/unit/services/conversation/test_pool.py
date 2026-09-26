"""T032: ConversationSessionPool — reuse, rebuild, bounds, expiry, locking, and retry."""

import logging
import threading
import time
from datetime import timedelta

import pytest

from app.services.conversation import SavedTurn, SessionKey, SessionKind, TurnRequest
from app.services.conversation.pool import ConversationSessionPool
from app.services.llm.base import LLMError
from app.services.llm.selection_types import LLMSelection
from tests.support.recording_session_provider import FakeClock, RecordingSessionProvider

STANDING = "Eres Lucía."
ROLEPLAY_7 = SessionKey(SessionKind.ROLEPLAY, "7")
ASK = SavedTurn("m1", "user", "Hola")
ANSWER = SavedTurn("m2", "assistant", "Buenos días")
FOLLOW_UP = SavedTurn("m3", "user", "Un billete")


@pytest.fixture()
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture()
def pool(clock) -> ConversationSessionPool:
    return ConversationSessionPool(max_live=3, idle_ttl=timedelta(minutes=30), clock=clock)


@pytest.fixture()
def provider() -> RecordingSessionProvider:
    return RecordingSessionProvider()


def _request(history, key=ROLEPLAY_7, guidance=None, opening=None) -> TurnRequest:
    return TurnRequest(key, STANDING, tuple(history), guidance, opening)


def _key(identifier: str) -> SessionKey:
    return SessionKey(SessionKind.ROLEPLAY, identifier)


def _turn(pool, provider, history, key=ROLEPLAY_7, ack: str | None = None) -> str:
    reply = "".join(pool.run_turn(provider, _request(history, key)))
    if ack is not None:
        pool.acknowledge(key, ack)
    return reply


class TestReuse:
    def test_a_matching_session_is_reused_for_the_next_turn(self, pool, provider):
        _turn(pool, provider, [ASK], ack="m2")

        _turn(pool, provider, [ASK, ANSWER, FOLLOW_UP])

        [session] = provider.opened
        assert [pending for pending, _ in session.replies] == [(ASK,), (FOLLOW_UP,)]

    def test_the_reply_is_the_sessions_tokens(self, pool, provider):
        assert _turn(pool, provider, [ASK]) == "Buenos días"

    def test_guidance_is_passed_to_the_session(self, pool, provider):
        list(pool.run_turn(provider, _request([ASK], guidance="recast")))

        assert provider.opened[0].replies == [((ASK,), "recast")]

    def test_an_opening_uses_the_opening_reply(self, pool, provider):
        list(pool.run_turn(provider, _request([], opening="Greet.")))

        assert provider.opened[0].openings == ["Greet."]

    def test_an_unacknowledged_reply_forces_a_rebuild(self, pool, provider):
        _turn(pool, provider, [ASK])

        _turn(pool, provider, [ASK, ANSWER, FOLLOW_UP])

        assert len(provider.opened) == 2
        assert provider.opened[0].is_closed


class TestRebuild:
    def test_a_changed_fingerprint_closes_and_reopens(self, pool, provider):
        _turn(pool, provider, [ASK], ack="m2")
        provider.selection = LLMSelection("fake", "other-model")

        _turn(pool, provider, [ASK, ANSWER, FOLLOW_UP])

        first, second = provider.opened
        assert first.is_closed
        assert second.history == (ASK, ANSWER)
        assert second.replies == [((FOLLOW_UP,), None)]

    def test_a_rebuild_is_logged_with_its_turn_count(self, pool, provider, caplog):
        with caplog.at_level(logging.INFO):
            _turn(pool, provider, [ASK, ANSWER, FOLLOW_UP])

        assert "session rebuilt key=roleplay:7 turns=3 generations=1" in caplog.text


class TestBounds:
    def test_opening_a_fourth_session_closes_the_least_recently_used(self, pool, provider):
        for identifier in ("1", "2", "3", "4"):
            _turn(pool, provider, [ASK], key=_key(identifier))

        assert [session.is_closed for session in provider.opened] == [True, False, False, False]
        assert not pool.is_live(_key("1"))

    def test_an_idle_session_expires_on_next_access(self, pool, provider, clock):
        _turn(pool, provider, [ASK], ack="m2")
        clock.advance(31)

        _turn(pool, provider, [ASK, ANSWER, FOLLOW_UP])

        assert provider.opened[0].is_closed
        assert len(provider.opened) == 2

    def test_evict_idle_closes_only_sessions_idle_past_the_ttl(self, pool, provider, clock):
        _turn(pool, provider, [ASK], key=_key("old"))
        clock.advance(20)
        _turn(pool, provider, [ASK], key=_key("fresh"))
        clock.advance(15)

        pool.evict_idle()

        old, fresh = provider.opened
        assert old.is_closed and not fresh.is_closed
        assert pool.is_live(_key("fresh"))

    def test_close_all_closes_every_session(self, pool, provider):
        for identifier in ("1", "2"):
            _turn(pool, provider, [ASK], key=_key(identifier))

        pool.close_all()

        assert all(session.is_closed for session in provider.opened)
        assert not pool.is_live(_key("1"))


class TestFailures:
    def test_a_retryable_failure_rebuilds_and_retries_once(self, pool, provider):
        provider.errors = [LLMError("process exited")]

        assert _turn(pool, provider, [ASK]) == "Buenos días"
        assert len(provider.opened) == 2
        assert provider.opened[0].is_closed

    def test_a_second_failure_propagates(self, pool, provider):
        provider.errors = [LLMError("first"), LLMError("second")]

        with pytest.raises(LLMError, match="second"):
            _turn(pool, provider, [ASK])
        assert len(provider.opened) == 2
        assert not pool.is_live(ROLEPLAY_7)

    def test_a_non_retryable_failure_propagates_without_a_rebuild(self, pool, provider):
        provider.errors = [LLMError("usage limit", can_retry=False)]

        with pytest.raises(LLMError, match="usage limit"):
            _turn(pool, provider, [ASK])
        assert len(provider.opened) == 1

    def test_a_failure_after_the_reply_began_is_retried_without_splicing(self, pool, provider):
        provider.mid_reply_errors = [LLMError("process exited mid-reply")]

        assert _turn(pool, provider, [ASK]) == "Buenos días"
        assert len(provider.opened) == 2
        assert provider.opened[0].is_closed

    def test_a_non_retryable_failure_after_the_reply_began_is_not_retried(self, pool, provider):
        provider.mid_reply_errors = [LLMError("usage limit", can_retry=False)]

        with pytest.raises(LLMError, match="usage limit"):
            _turn(pool, provider, [ASK])
        assert len(provider.opened) == 1
        assert not pool.is_live(ROLEPLAY_7)

    def test_an_early_closed_reply_discards_the_session(self, pool, provider):
        tokens = pool.run_turn(provider, _request([ASK]))
        next(tokens)

        tokens.close()

        assert provider.opened[0].is_closed
        assert not pool.is_live(ROLEPLAY_7)


class TestLocking:
    def _run_in_thread(self, pool, provider, key) -> threading.Thread:
        thread = threading.Thread(target=_turn, args=(pool, provider, [ASK], key))
        thread.start()
        return thread

    def _wait_for_starts(self, provider, count: int) -> None:
        deadline = time.monotonic() + 2
        while sum(1 for event, _ in provider.log if event == "start") < count:
            assert time.monotonic() < deadline, "generation never started"
            time.sleep(0.005)

    def test_turns_on_one_key_run_one_after_another(self, pool, provider):
        gate = provider.gate()
        first = self._run_in_thread(pool, provider, ROLEPLAY_7)
        self._wait_for_starts(provider, 1)
        second = self._run_in_thread(pool, provider, ROLEPLAY_7)
        time.sleep(0.05)

        assert [event for event, _ in provider.log] == ["start"]
        gate.set()
        first.join(2)
        second.join(2)
        assert [event for event, _ in provider.log] == ["start", "end", "start", "end"]

    def test_turns_on_different_keys_run_concurrently(self, pool, provider):
        gate = provider.gate()
        first = self._run_in_thread(pool, provider, _key("a"))
        second = self._run_in_thread(pool, provider, _key("b"))

        self._wait_for_starts(provider, 2)

        gate.set()
        first.join(2)
        second.join(2)

    def test_evict_idle_never_closes_a_session_mid_turn(self, pool, provider, clock):
        gate = provider.gate()
        running = self._run_in_thread(pool, provider, ROLEPLAY_7)
        self._wait_for_starts(provider, 1)
        clock.advance(45)

        pool.evict_idle()

        assert not provider.opened[0].is_closed
        gate.set()
        running.join(2)


class TestWarmAndLifecycle:
    def test_warm_opens_and_warms_without_generating(self, pool, provider):
        pool.warm(provider, ROLEPLAY_7, STANDING, [ASK, ANSWER])

        [session] = provider.opened
        assert session.warm_count == 1
        assert session.replies == [] and session.openings == []
        assert pool.is_live(ROLEPLAY_7)

    def test_warm_leaves_a_matching_live_session_alone(self, pool, provider):
        pool.warm(provider, ROLEPLAY_7, STANDING, [ASK, ANSWER])

        pool.warm(provider, ROLEPLAY_7, STANDING, [ASK, ANSWER])

        assert len(provider.opened) == 1

    def test_a_warmed_session_is_reused_by_the_next_turn(self, pool, provider):
        pool.warm(provider, ROLEPLAY_7, STANDING, [ASK, ANSWER])

        _turn(pool, provider, [ASK, ANSWER, FOLLOW_UP])

        assert len(provider.opened) == 1

    def test_is_live_does_not_refresh_the_idle_clock(self, pool, provider, clock):
        _turn(pool, provider, [ASK])
        clock.advance(20)
        pool.is_live(ROLEPLAY_7)
        clock.advance(15)

        pool.evict_idle()

        assert provider.opened[0].is_closed

    def test_end_closes_only_that_session(self, pool, provider):
        _turn(pool, provider, [ASK], key=_key("1"))
        _turn(pool, provider, [ASK], key=_key("2"))

        pool.end(_key("1"))

        assert [session.is_closed for session in provider.opened] == [True, False]

    def test_acknowledging_an_absent_session_is_ignored(self, pool):
        pool.acknowledge(ROLEPLAY_7, "m2")

        assert not pool.is_live(ROLEPLAY_7)
