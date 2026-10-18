"""010 T034: the memory keeper's parser, grounding rule, chunks and prompt (R6, contracts §8–§9)."""

import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from app.podcasts.catalog import (
    MAX_POINTS_PER_EPISODE,
    MEMORY_CHUNK_CHARACTERS,
    REMEMBERED_POINT_MAX_LENGTH,
)
from app.podcasts.prompts import MEMORY_JSON_SCHEMA
from app.podcasts.services.series_memory import (
    MemoryStores,
    SeriesMemoryKeeper,
    UnreadableMemoryError,
    parse_memory_reply,
)
from app.podcasts.services.series_storage import MemoryReply, PointText
from app.podcasts.services.sqlite_series_storage import SQLiteSeriesStorage
from app.podcasts.services.sqlite_storage import SQLitePodcastStorage
from app.services.llm.base import LLMError
from tests.support.scratch_database import make_session
from tests.support.scripted_memory_llm import ScriptedMemoryLLM
from tests.support.series_records import (
    add_host_lines,
    add_learner_lines,
    make_series,
    reply,
    series_episode,
)

TOPIC = {"conversation_language": "los bostezos", "english": "Why we yawn"}
HATES_MORNINGS = {"conversation_language": "Odia las mañanas.", "english": "You hate mornings."}


def _raw(topic=TOPIC, about_learner=(HATES_MORNINGS,)) -> str:
    return json.dumps({"topic": topic, "about_learner": list(about_learner)})


# --- the parser ----------------------------------------------------------------------------


def test_a_valid_reply_gives_the_topic_and_learner_points():
    parsed = parse_memory_reply(_raw())

    assert parsed == MemoryReply(
        PointText("los bostezos", "Why we yawn"),
        (PointText("Odia las mañanas.", "You hate mornings."),),
    )


def test_texts_are_trimmed_and_cut_to_the_point_length():
    long_text = "  " + "a" * (REMEMBERED_POINT_MAX_LENGTH + 40) + "  "
    point = {"conversation_language": long_text, "english": " You do. "}

    parsed = parse_memory_reply(_raw(about_learner=(point,)))

    assert parsed.about_learner[0] == PointText("a" * REMEMBERED_POINT_MAX_LENGTH, "You do.")


def test_no_topic_and_no_learner_points_are_accepted():
    assert parse_memory_reply(_raw(topic=None, about_learner=())) == MemoryReply(None, ())


def test_a_blank_topic_counts_as_none():
    blank = {"conversation_language": " ", "english": ""}

    assert parse_memory_reply(_raw(topic=blank)).topic is None


def test_more_than_three_learner_points_keep_the_first_three():
    points = [{"conversation_language": f"p{n}", "english": f"e{n}"} for n in range(5)]

    parsed = parse_memory_reply(_raw(about_learner=points))

    assert [p.conversation_language for p in parsed.about_learner] == ["p0", "p1", "p2"]
    assert len(parsed.about_learner) == MAX_POINTS_PER_EPISODE


@pytest.mark.parametrize(
    "raw", ["not json", "[]", '{"topic": null}', '{"topic": 3, "about_learner": []}']
)
def test_an_unreadable_reply_is_an_llm_error(raw):
    with pytest.raises(UnreadableMemoryError) as raised:
        parse_memory_reply(raw)

    assert isinstance(raised.value, LLMError)


# --- the keeper over real storage ----------------------------------------------------------


@pytest.fixture
def session(tmp_path: Path):
    db_session = make_session(tmp_path / "memory.db")
    yield db_session
    db_session.close()


@pytest.fixture
def series(session):
    return make_series(session)


@pytest.fixture
def llm() -> ScriptedMemoryLLM:
    return ScriptedMemoryLLM()


@pytest.fixture
def keeper(session, llm) -> SeriesMemoryKeeper:
    @contextmanager
    def stores():
        yield MemoryStores(SQLitePodcastStorage(session), SQLiteSeriesStorage(session))

    return SeriesMemoryKeeper(llm, stores)


def _remembered(session, series) -> list[tuple[str, str]]:
    points = SQLiteSeriesStorage(session).remembered(series.series_id)
    return [(point.kind, point.conversation_language) for point in points]


def test_a_catch_up_writes_the_reply_and_moves_the_marker(session, series, keeper, llm):
    episode_id = series_episode(session, series, 1)
    add_host_lines(session, episode_id, "¡Hola! ¿Cómo te va la mañana?")
    last = add_learner_lines(session, episode_id, "Odio las mañanas.")[-1]
    llm.queue(json.loads(_raw()))

    keeper.catch_up(series.series_id)

    assert _remembered(session, series) == [
        ("learner", "Odia las mañanas."),
        ("topic", "los bostezos"),
    ]
    assert SQLiteSeriesStorage(session).pending_episodes(series.series_id) == ()
    assert last is not None


def test_learner_points_from_a_chunk_without_learner_lines_are_dropped(
    session, series, keeper, llm
):
    episode_id = series_episode(session, series, 1)
    add_host_lines(session, episode_id, "Hoy hablamos de los bostezos.", "A mí me encanta dormir.")
    llm.queue(json.loads(_raw()))

    keeper.catch_up(series.series_id)

    assert _remembered(session, series) == [("topic", "los bostezos")]


def test_long_episodes_are_read_in_chunks_one_call_each(session, series, keeper, llm):
    episode_id = series_episode(session, series, 1)
    line = "x" * (MEMORY_CHUNK_CHARACTERS // 3 - 20)
    add_host_lines(session, episode_id, *[line] * 7)

    keeper.catch_up(series.series_id)

    assert len(llm.calls) == 3
    assert all(
        len(prompt.split("Transcript:\n")[1].split("\n\n")[0]) <= MEMORY_CHUNK_CHARACTERS
        for prompt in llm.prompts
    )


def test_an_episode_with_too_few_unread_lines_makes_no_call(session, series, keeper, llm):
    episode_id = series_episode(session, series, 1)
    add_host_lines(session, episode_id, "¡Hola!")

    keeper.catch_up(series.series_id)

    assert llm.calls == []


def test_a_provider_failure_is_raised_and_leaves_the_marker(session, series, keeper, llm):
    episode_id = series_episode(session, series, 1)
    add_host_lines(session, episode_id, "¡Hola!", "¿Qué tal?")
    llm.queue(LLMError("ollama down", "Ollama isn't running."))

    with pytest.raises(LLMError):
        keeper.catch_up(series.series_id)

    assert len(SQLiteSeriesStorage(session).pending_episodes(series.series_id)) == 1


# --- the prompt ----------------------------------------------------------------------------


def test_the_prompt_labels_hosts_by_name_and_the_learner_as_learner(session, series, keeper, llm):
    episode_id = series_episode(session, series, 1)
    add_host_lines(session, episode_id, "¿Cómo te va la mañana?")
    add_learner_lines(session, episode_id, "Odio las mañanas.")

    keeper.catch_up(series.series_id)

    assert "Hugo: ¿Cómo te va la mañana?" in llm.last_prompt
    assert "Learner: Odio las mañanas." in llm.last_prompt


def test_the_prompt_lists_what_is_already_remembered(session, series, keeper, llm):
    first = series_episode(session, series, 1)
    SQLiteSeriesStorage(session).remember(
        series.series_id, first, reply("el sueño", "Tiene un perro."), None
    )
    second = series_episode(session, series, 2)
    add_host_lines(session, second, "¡Hola!", "¿Qué tal?")

    keeper.catch_up(series.series_id)

    assert "el sueño" in llm.last_prompt and "Tiene un perro." in llm.last_prompt


def test_the_prompt_states_the_rules_and_names_languages(session, series, keeper, llm):
    episode_id = series_episode(session, series, 1)
    add_host_lines(session, episode_id, "¡Hola!", "¿Qué tal?")

    keeper.catch_up(series.series_id)

    prompt = llm.last_prompt
    assert "only from lines labelled Learner" in prompt
    assert "Never note anything a host said" in prompt
    assert "No guesses" in prompt
    assert "empty list" in prompt
    assert "one short phrase" in prompt
    assert "Spanish" in prompt and "English" in prompt
    assert " es " not in prompt


def test_the_reply_follows_the_memory_schema_with_at_most_three_learner_points(
    session, series, keeper, llm
):
    episode_id = series_episode(session, series, 1)
    add_host_lines(session, episode_id, "¡Hola!", "¿Qué tal?")

    keeper.catch_up(series.series_id)

    assert llm.schemas == [MEMORY_JSON_SCHEMA]
    assert MEMORY_JSON_SCHEMA["properties"]["about_learner"]["maxItems"] == MAX_POINTS_PER_EPISODE
