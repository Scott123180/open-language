"""T033: ConversationEngine is the routers' one entry point to conversation sessions."""

from datetime import timedelta

import pytest

from app.services.conversation import (
    ConversationEngine,
    SavedTurn,
    SessionKey,
    SessionKind,
    TurnRequest,
)
from app.services.conversation.pool import ConversationSessionPool
from tests.support.recording_session_provider import FakeClock, RecordingSessionProvider

STANDING = "Eres Lucía."
KEY = SessionKey(SessionKind.ROLEPLAY, "7")
OTHER_KEY = SessionKey(SessionKind.ROLEPLAY, "8")
ASK = SavedTurn("m1", "user", "Hola")


@pytest.fixture()
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture()
def engine(clock) -> ConversationEngine:
    return ConversationEngine(ConversationSessionPool(3, timedelta(minutes=30), clock))


@pytest.fixture()
def provider() -> RecordingSessionProvider:
    return RecordingSessionProvider()


def _turn(engine, provider, history, key=KEY, guidance=None, opening=None) -> str:
    request = TurnRequest(key, STANDING, tuple(history), guidance, opening)
    return "".join(engine.stream_turn(provider, request))


def test_an_opening_request_asks_for_the_opening_reply(engine, provider):
    _turn(engine, provider, [], opening="Greet the learner.")

    assert provider.opened[0].openings == ["Greet the learner."]
    assert provider.opened[0].replies == []


def test_a_learner_turn_asks_for_a_reply_with_its_guidance(engine, provider):
    _turn(engine, provider, [ASK], guidance="recast")

    assert provider.opened[0].replies == [((ASK,), "recast")]


def test_acknowledge_reaches_the_live_session(engine, provider):
    _turn(engine, provider, [ASK])

    engine.acknowledge(KEY, "m2")

    assert provider.opened[0].acknowledged == ["m2"]


def test_warm_opens_the_session_without_generating(engine, provider):
    engine.warm(provider, KEY, STANDING, [SavedTurn("m1", "assistant", "¡Hola!")])

    [session] = provider.opened
    assert session.warm_count == 1
    assert provider.reply_count == 0 and session.openings == []


def test_is_live_answers_without_opening_anything(engine, provider):
    assert engine.is_live(KEY) is False
    assert provider.opened == []


def test_end_closes_that_session_only(engine, provider):
    _turn(engine, provider, [ASK], key=KEY)
    _turn(engine, provider, [ASK], key=OTHER_KEY)

    engine.end(KEY)

    assert [session.is_closed for session in provider.opened] == [True, False]


def test_evict_idle_delegates_to_the_pool(engine, provider, clock):
    _turn(engine, provider, [ASK])
    clock.advance(31)

    engine.evict_idle()

    assert provider.opened[0].is_closed


def test_close_closes_every_session(engine, provider):
    _turn(engine, provider, [ASK], key=KEY)
    _turn(engine, provider, [ASK], key=OTHER_KEY)

    engine.close()

    assert all(session.is_closed for session in provider.opened)


def test_rebuild_of_long_history_generates_exactly_once(engine, provider):
    history = [
        SavedTurn(f"m{index}", "assistant" if index % 2 else "user", f"turn {index}")
        for index in range(20)
    ]
    history.append(SavedTurn("m20", "user", "¿Y ahora?"))

    _turn(engine, provider, history)

    [session] = provider.opened
    assert provider.reply_count == 1
    assert session.history == tuple(history[:-1])
