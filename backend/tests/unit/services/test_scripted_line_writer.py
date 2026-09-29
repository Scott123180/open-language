"""T021: the scripted line writer, the test double every podcast integration test relies on."""

import pytest

from app.services.conversation import SavedTurn, SessionCapableProvider, SessionKey, SessionKind
from app.services.llm.base import LLMError
from tests.support.scripted_line_writer import ScriptedLineWriter

KEY = SessionKey(SessionKind.PODCAST, "57")
CUE = SavedTurn("c0", "user", "[Producer note] Next: Lucía.")


def _reply(writer: ScriptedLineWriter, pending=(CUE,), prompt="prompt") -> str:
    session = writer.open_session(KEY, prompt, ())
    return "".join(session.reply(pending, None))


def test_it_is_a_session_capable_provider():
    assert isinstance(ScriptedLineWriter(), SessionCapableProvider)


def test_each_reply_is_the_next_scripted_line():
    writer = ScriptedLineWriter(["¡Hola!", "¿Qué tal?"])
    session = writer.open_session(KEY, "prompt", ())

    assert "".join(session.reply((CUE,), None)) == "¡Hola!"
    assert "".join(session.reply((SavedTurn("c1", "user", "cue"),), None)) == "¿Qué tal?"


def test_an_unscripted_reply_is_a_numbered_default_line():
    writer = ScriptedLineWriter()

    assert _reply(writer) != _reply(writer)


def test_lines_can_be_scripted_later():
    writer = ScriptedLineWriter()

    writer.script("Marco: ¡Hola!")

    assert _reply(writer) == "Marco: ¡Hola!"


def test_every_prompt_and_pending_turn_is_recorded():
    writer = ScriptedLineWriter()

    _reply(writer, prompt="standing")

    assert writer.received == [("standing", (CUE,))]


def test_sessions_opened_are_counted():
    writer = ScriptedLineWriter()

    _reply(writer)
    _reply(writer)

    assert writer.open_count == 2


def test_the_next_reply_can_fail():
    writer = ScriptedLineWriter(["¡Hola!"])
    writer.fail_next(LLMError("down", "The AI is not responding."))

    with pytest.raises(LLMError):
        _reply(writer)
    assert _reply(writer) == "¡Hola!"


def test_a_session_tracks_the_turns_it_has_taken_in():
    writer = ScriptedLineWriter()
    session = writer.open_session(KEY, "prompt", (SavedTurn("p1", "assistant", "hola"),))

    list(session.reply((CUE,), None))
    session.acknowledge("p2")

    assert tuple(session.synced_turn_ids) == ("p1", "c0", "p2")
