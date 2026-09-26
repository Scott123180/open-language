"""T031: what an Ollama session does that a Claude session doesn't (research R-13)."""

import pytest

from app.services.conversation.session import (
    SavedTurn,
    SessionFingerprint,
    SessionKey,
    SessionKind,
)
from app.services.llm.base import LLMError
from app.services.llm.ollama import OllamaLLMProvider
from tests.support.fake_ollama_client import ScriptedOllamaClient

TTL_MINUTES = 30
STANDING = "Eres Lucía, taquillera."
GUIDANCE = " Recast the learner's mistake naturally."
GREETING = SavedTurn("m1", "assistant", "¡Hola!")
ASK = SavedTurn("m2", "user", "Un billete.")
RETRY = SavedTurn("m3", "user", "Un billete, por favor.")
KEY = SessionKey(SessionKind.ROLEPLAY, "7")


@pytest.fixture()
def client() -> ScriptedOllamaClient:
    return ScriptedOllamaClient()


def _provider(client) -> OllamaLLMProvider:
    return OllamaLLMProvider(client, "llama3.2", TTL_MINUTES)


def _wire(role: str, content: str) -> dict:
    return {"role": role, "content": content}


def test_every_chat_keeps_the_model_loaded_for_the_idle_ttl(client):
    session = _provider(client).open_session(KEY, STANDING, [GREETING])

    list(session.reply([ASK], None))

    assert client.chat_calls[0]["keep_alive"] == "30m"
    assert client.chat_calls[0]["stream"] is True


def test_warm_preloads_with_an_empty_prompt_and_never_chats(client):
    _provider(client).open_session(KEY, STANDING, [GREETING]).warm()

    assert client.generate_calls == [{"model": "llama3.2", "prompt": "", "keep_alive": "30m"}]
    assert client.chat_calls == []


def test_guidance_is_appended_to_the_system_message_as_today(client):
    session = _provider(client).open_session(KEY, STANDING, [GREETING])

    list(session.reply([ASK], GUIDANCE))

    assert client.chat_calls[0]["messages"][0] == _wire("system", STANDING + GUIDANCE)


def test_guidance_does_not_carry_into_the_next_turn(client):
    session = _provider(client).open_session(KEY, STANDING, [GREETING])
    list(session.reply([ASK], GUIDANCE))
    session.acknowledge("m9")

    list(session.reply([SavedTurn("m10", "user", "Gracias.")], None))

    assert client.chat_calls[1]["messages"][0] == _wire("system", STANDING)


def test_two_pending_learner_turns_are_consecutive_user_messages(client):
    session = _provider(client).open_session(KEY, STANDING, [GREETING])

    list(session.reply([ASK, RETRY], None))

    assert client.chat_calls[0]["messages"] == [
        _wire("system", STANDING),
        _wire("assistant", "¡Hola!"),
        _wire("user", "Un billete."),
        _wire("user", "Un billete, por favor."),
    ]


def test_opening_on_empty_history_sends_system_then_the_instruction(client):
    session = _provider(client).open_session(KEY, STANDING, [])

    list(session.reply_to_opening("Greet the learner."))

    assert client.chat_calls[0]["messages"] == [
        _wire("system", STANDING),
        _wire("user", "Greet the learner."),
    ]


def test_opening_instruction_is_never_recorded_as_a_turn(client):
    session = _provider(client).open_session(KEY, STANDING, [])
    list(session.reply_to_opening("Greet the learner."))

    session.acknowledge("m1")

    assert list(session.synced_turn_ids) == ["m1"]


def test_opening_instruction_is_absent_from_the_next_request(client):
    session = _provider(client).open_session(KEY, STANDING, [])
    list(session.reply_to_opening("Greet the learner."))
    session.acknowledge("m1")

    list(session.reply([SavedTurn("m2", "user", "Hola")], None))

    contents = [message["content"] for message in client.chat_calls[1]["messages"]]
    assert "Greet the learner." not in contents


def test_fingerprint_has_no_effort(client):
    fingerprint = _provider(client).session_fingerprint(STANDING)

    assert fingerprint.effort == ""
    assert fingerprint.selection.model == "llama3.2"
    assert fingerprint.standing_prompt_digest == SessionFingerprint.digest_prompt(STANDING)


def test_a_session_carries_the_providers_fingerprint(client):
    provider = _provider(client)

    assert provider.open_session(KEY, STANDING, []).fingerprint == provider.session_fingerprint(
        STANDING
    )


def test_warm_failure_marks_the_session_broken(client):
    session = _provider(client).open_session(KEY, STANDING, [])
    client.fail_with(ConnectionError("refused"))

    with pytest.raises(LLMError):
        session.warm()
    assert session.is_broken is True
