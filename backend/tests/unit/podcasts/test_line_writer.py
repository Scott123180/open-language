"""011 T032: LineWriter, a host line streamed into kept sentences (research R13)."""

from datetime import timedelta

import pytest

from app.podcasts.catalog import PODCAST_FORMATS
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.line_address import LineAddress
from app.podcasts.services.line_writer import (
    EmptyLineError,
    KeptSentence,
    LineLostError,
    LineRequest,
    LineWriter,
    WrittenLine,
)
from app.podcasts.services.sanitiser import LineSanitiser, StreamingSanitiser
from app.services.conversation import (
    ConversationEngine,
    ConversationSessionPool,
    SavedTurn,
    SessionKey,
    SessionKind,
    TurnRequest,
)
from app.services.llm.base import LLMError
from tests.support.recording_session_provider import FakeClock
from tests.support.scripted_line_writer import ScriptedLineWriter

KEY = SessionKey(SessionKind.PODCAST, "57")
LUCIA = Host("lead", "Lucía", "enthusiast", "es_AR-daniela-high", "host")
MARCO = Host("second", "Marco", "dry_sceptic", "es_ES-davefx-medium", "co_host")
CAST = Cast.for_format(PODCAST_FORMATS["panel"], LUCIA, MARCO)
STREAM_ID = "b3f1"


def _sanitiser() -> StreamingSanitiser:
    address = LineAddress.for_episode(CAST, "Sam", "lead", "es", is_listening=False)
    return StreamingSanitiser(LineSanitiser.for_speaker("Lucía", ("Marco",), "Sam", "es"), address)


@pytest.fixture
def writer() -> ScriptedLineWriter:
    return ScriptedLineWriter()


@pytest.fixture
def engine() -> ConversationEngine:
    return ConversationEngine(ConversationSessionPool(3, timedelta(minutes=30), FakeClock()))


def _request() -> LineRequest:
    turn = TurnRequest(KEY, "prompt", (SavedTurn("c0", "user", "cue"),), None, None)
    return LineRequest(turn, _sanitiser, STREAM_ID)


async def _events(engine, writer) -> list:
    return [event async for event in LineWriter(engine, writer).write(_request())]


async def test_each_kept_sentence_is_given_as_it_completes(engine, writer):
    writer.script_tokens(["Hola a ", "todos. Hoy hablamos ", "de pan. ¡Qué rico!"])

    events = await _events(engine, writer)

    assert events[:3] == [
        KeptSentence("Hola a todos."),
        KeptSentence("Hoy hablamos de pan."),
        KeptSentence("¡Qué rico!"),
    ]


async def test_the_written_line_is_its_sentences_joined_by_single_spaces(engine, writer):
    writer.script_tokens(["Hola a todos.\n", "Hoy hablamos de pan."])

    *_parts, written = await _events(engine, writer)

    assert written.text == "Hola a todos. Hoy hablamos de pan."
    assert written.was_trimmed is False


async def test_the_written_line_says_who_it_is_for_without_its_tag(engine, writer):
    writer.script_tokens(["Hoy hablamos de pan. ", "¿Y tú, comes pan? [@Sam]"])

    *_parts, written = await _events(engine, writer)

    assert (written.text, written.addressee) == (
        "Hoy hablamos de pan. ¿Y tú, comes pan?",
        "learner",
    )
    assert written.is_address_from_tag is True


async def test_a_line_cut_by_another_speaker_keeps_what_came_before(engine, writer):
    writer.script_tokens(["¡Qué rica la paella! Marco: Yo no. Lucía: sí."])

    events = await _events(engine, writer)

    assert events == [
        KeptSentence("¡Qué rica la paella!"),
        WrittenLine("¡Qué rica la paella!", True, None, False),
    ]


@pytest.mark.parametrize("first", ["Marco: Yo no estoy de acuerdo.", "(silencio)"])
async def test_a_line_cut_or_empty_before_its_first_sentence_is_written_again(
    engine, writer, first
):
    writer.script(first, "¡Hola a todos!")

    events = await _events(engine, writer)

    assert events == [
        KeptSentence("¡Hola a todos!"),
        WrittenLine("¡Hola a todos!", False, None, False),
    ]


async def test_two_empty_attempts_fail_and_end_the_session(engine, writer):
    writer.script("Marco: Hola.", "Marco: Adiós.")

    with pytest.raises(EmptyLineError):
        await _events(engine, writer)
    assert not engine.is_live(KEY)


async def test_a_retryable_error_before_any_sentence_is_retried_once(engine, writer):
    writer.fail_next(LLMError("process exited"))
    writer.script("¡Hola a todos!")

    events = await _events(engine, writer)

    assert events[-1].text == "¡Hola a todos!"


async def test_an_error_before_any_sentence_is_the_providers_own(engine, writer):
    writer.fail_next(LLMError("usage limit", "You've reached your limit.", can_retry=False))

    with pytest.raises(LLMError) as raised:
        await _events(engine, writer)
    assert not isinstance(raised.value, LineLostError)
    assert raised.value.user_message == "You've reached your limit."


async def test_an_error_after_a_sentence_loses_the_line_with_its_stream_id(engine, writer):
    writer.script_tokens(["Hola a todos. ", "Hoy hablamos ", "de pan."])
    writer.fail_after_tokens(2, LLMError("process exited mid-line"))
    seen = []

    with pytest.raises(LineLostError) as raised:
        async for event in LineWriter(engine, writer).write(_request()):
            seen.append(event)

    assert seen == [KeptSentence("Hola a todos.")]
    assert raised.value.stream_id == STREAM_ID
    assert raised.value.user_message == "The host lost their words. Press Retry."
    assert not engine.is_live(KEY)
