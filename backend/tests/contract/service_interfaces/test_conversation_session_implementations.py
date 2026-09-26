"""T030: the session contract (contracts/api.md §2.6), run over every provider's session.

Adding a provider means adding one entry to `_HARNESSES`. The test bodies never change.
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial

import pytest

from app.config import Settings
from app.services.conversation import ConversationSession, SavedTurn, SessionKey, SessionKind
from app.services.llm.base import LLMError
from app.services.llm.claude_code import ClaudeCodeLLMProvider
from app.services.llm.ollama import OllamaLLMProvider
from tests.support.fake_availability import FakeAvailability
from tests.support.fake_ollama_client import ScriptedOllamaClient
from tests.support.scripted_claude_runner import ScriptedClaudeCodeRunner

STANDING = "Eres Lucía, taquillera en la estación de Atocha."
GUIDANCE = "TURN-GUIDANCE-MARKER: recast the learner's mistake."
HISTORY = (
    SavedTurn("m1", "assistant", "¡Buenos días! ¿Adónde viaja?"),
    SavedTurn("m2", "user", "A Sevilla, por favor."),
    SavedTurn("m3", "assistant", "¿Ida y vuelta?"),
)
PENDING = (SavedTurn("m4", "user", "Solo ida."),)
NEXT = (SavedTurn("m6", "user", "¿Cuánto cuesta?"),)
_TTL_MINUTES = 30
KEY = SessionKey(SessionKind.ROLEPLAY, "7")


@dataclass(frozen=True)
class SessionHarness:
    """Opens sessions over a recording backend and reports what each generation was sent."""

    open: Callable[[str, Sequence[SavedTurn]], ConversationSession]
    requests: Callable[[], list[str]]
    break_backend: Callable[[], None]


def _ollama_harness() -> SessionHarness:
    client = ScriptedOllamaClient()
    provider = OllamaLLMProvider(client, "llama3.2", _TTL_MINUTES)
    return SessionHarness(
        open=partial(provider.open_session, KEY),
        requests=lambda: [
            json.dumps(call["messages"], ensure_ascii=False) for call in client.chat_calls
        ],
        break_backend=lambda: client.fail_with(ConnectionError("daemon stopped")),
    )


def _claude_requests(runner: ScriptedClaudeCodeRunner) -> list[str]:
    """One request per user line, holding every line sent since the previous one."""
    requests: list[str] = []
    since_last: list[str] = []
    for process in runner.processes:
        for message in process.sent_messages:
            since_last.append(message["message"]["content"])
            if message["type"] == "user":
                requests.append("\n".join(since_last))
                since_last = []
    return requests


def _claude_harness() -> SessionHarness:
    runner = ScriptedClaudeCodeRunner()
    provider = ClaudeCodeLLMProvider(
        runner, FakeAvailability(), Settings(_env_file=None), "sonnet", "low"
    )
    return SessionHarness(
        open=partial(provider.open_session, KEY),
        requests=lambda: _claude_requests(runner),
        break_backend=lambda: setattr(runner, "is_dead", True),
    )


_HARNESSES: dict[str, Callable[[], SessionHarness]] = {
    "ollama": _ollama_harness,
    "claude": _claude_harness,
}


@pytest.fixture(params=sorted(_HARNESSES))
def session_factory(request) -> SessionHarness:
    return _HARNESSES[request.param]()


def _reply(session: ConversationSession, pending, guidance=None) -> str:
    return "".join(session.reply(pending, guidance))


def test_first_reply_is_one_request_carrying_history_and_pending(session_factory):
    session = session_factory.open(STANDING, HISTORY)

    _reply(session, PENDING)

    [request] = session_factory.requests()
    for turn in (*HISTORY, *PENDING):
        assert turn.content in request


def test_acknowledge_records_pending_ids_then_the_reply_id(session_factory):
    session = session_factory.open(STANDING, HISTORY)
    _reply(session, PENDING)

    session.acknowledge("m5")

    assert list(session.synced_turn_ids)[-2:] == ["m4", "m5"]


def test_a_second_reply_regenerates_no_earlier_turn(session_factory):
    session = session_factory.open(STANDING, HISTORY)
    _reply(session, PENDING)
    session.acknowledge("m5")

    _reply(session, NEXT)

    assert len(session_factory.requests()) == 2
    assert NEXT[0].content in session_factory.requests()[1]


def test_guidance_reaches_only_its_own_turn(session_factory):
    session = session_factory.open(STANDING, HISTORY)
    _reply(session, PENDING, GUIDANCE)
    session.acknowledge("m5")

    _reply(session, NEXT)

    first, second = session_factory.requests()
    assert GUIDANCE in first
    assert GUIDANCE not in second


def test_warm_produces_no_reply(session_factory):
    session_factory.open(STANDING, HISTORY).warm()

    assert session_factory.requests() == []


def test_close_is_idempotent_and_ends_the_session(session_factory):
    session = session_factory.open(STANDING, HISTORY)

    session.close()
    session.close()

    with pytest.raises(LLMError):
        _reply(session, PENDING)


def test_a_mid_turn_failure_breaks_the_session_with_a_user_message(session_factory):
    session = session_factory.open(STANDING, HISTORY)
    session_factory.break_backend()

    with pytest.raises(LLMError) as raised:
        _reply(session, PENDING)

    assert raised.value.user_message.strip()
    assert session.is_broken is True
