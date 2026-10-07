"""Adherence benchmark for any practice language, against the real default local model (R8).

006's SC-002, made language-independent by 008: each scenario's scripted learner turns come from
the language's evaluation set, and every reply is checked for words of English and the other
practice languages. Deselected by default (`-m "not benchmark"` in pyproject), so CI stays
hermetic. `kit.sh bench <code>` runs it for one language; by hand, from `backend/`:

    OPEN_LANGUAGE_BENCH_LANGUAGE=de backend/.venv/bin/pytest -m benchmark -s \
        tests/integration/practice_languages/test_adherence_benchmark.py

The results and the review sheet are written before the assertion runs, so a missed threshold
still leaves the complete evidence behind.
"""

import datetime
from dataclasses import dataclass

import pytest

from app.config import get_settings
from app.conversation_levels import ConversationLevel
from app.routers.chat import _standing_roleplay_prompt
from app.services.conversation import (
    ConversationEngine,
    SavedTurn,
    SessionKey,
    SessionKind,
    TurnRequest,
)
from app.services.conversation.pool import ConversationSessionPool
from app.services.llm.catalog import DEFAULT_PROVIDER_ID
from app.services.llm.registry import build_llm_provider
from app.services.llm.selection_types import LLMSelection
from app.services.scenario.static import StaticScenarioProvider
from app.services.storage.base import ConversationRecord
from tests.integration.practice_languages.bench_environment import (
    BenchmarkResult,
    bench_languages,
    bench_output_dir,
    record_benchmark,
    write_review_sheet,
)
from tests.integration.practice_languages.evaluation_set import evaluation_set
from tests.integration.practice_languages.text_purity import foreign_words, other_languages
from tests.support.engine_overrides import TEST_IDLE_TTL, TEST_MAX_LIVE

pytestmark = pytest.mark.benchmark

NATIVE_LANGUAGE = "en"
MIN_PURE_SHARE = 0.95
THRESHOLD = "≥ 95%"


@dataclass(frozen=True, slots=True)
class Reply:
    scenario_id: str
    learner_text: str
    text: str
    flagged: tuple[str, ...]

    @property
    def is_pure(self) -> bool:
        """An empty reply is a failure, never a trivially clean one."""
        return bool(self.text.strip()) and not self.flagged


def _conversation(code: str, scenario_id: str, conversation_id: int) -> ConversationRecord:
    title = next(s.title for s in StaticScenarioProvider().get_all() if s.id == scenario_id)
    return ConversationRecord(
        id=conversation_id,
        scenario_id=scenario_id,
        scenario_title=title,
        target_language=code,
        native_language=NATIVE_LANGUAGE,
        status="active",
        started_at=datetime.datetime.now(datetime.UTC),
        ended_at=None,
        llm_model=get_settings().ollama_model,
    )


class ScriptedPlayer:
    """Plays scripted learner turns through the real engine and the real default model."""

    def __init__(self, code: str) -> None:
        settings = get_settings()
        self._code = code
        self._others = other_languages(code)
        self._provider = build_llm_provider(
            LLMSelection(DEFAULT_PROVIDER_ID, settings.ollama_model), settings
        )
        pool = ConversationSessionPool(
            TEST_MAX_LIVE, TEST_IDLE_TTL, clock=lambda: datetime.datetime.now(datetime.UTC)
        )
        self._engine = ConversationEngine(pool)
        self._next_id = 0

    def play(self, scenario_id: str, turns: tuple[str, ...]) -> list[Reply]:
        self._next_id += 1
        record = _conversation(self._code, scenario_id, self._next_id)
        prompt = _standing_roleplay_prompt(
            record, StaticScenarioProvider(), ConversationLevel.NATURAL
        )
        key = SessionKey(SessionKind.ROLEPLAY, str(self._next_id))
        history: list[SavedTurn] = []
        replies = [
            self._judged(scenario_id, turn, self._reply(key, prompt, history, turn))
            for turn in turns
        ]
        self._engine.end(key)
        return replies

    def _judged(self, scenario_id: str, turn: str, reply: str) -> Reply:
        return Reply(
            scenario_id, turn, reply, tuple(foreign_words(reply, self._code, self._others))
        )

    def _reply(self, key: SessionKey, prompt: str, history: list[SavedTurn], text: str) -> str:
        history.append(SavedTurn(f"u{len(history)}", "user", text))
        request = TurnRequest(key, prompt, tuple(history), None, None)
        reply = "".join(self._engine.stream_turn(self._provider, request)).strip()
        reply_id = f"a{len(history)}"
        self._engine.acknowledge(key, reply_id)
        history.append(SavedTurn(reply_id, "assistant", reply))
        return reply


def _record(code: str, replies: list[Reply]) -> BenchmarkResult:
    directory = bench_output_dir(code)
    rows = [
        (r.scenario_id, r.learner_text, r.text, ", ".join(r.flagged)) for r in replies if r.flagged
    ]
    sheet = write_review_sheet(directory, code, other_languages(code), rows)
    pure = sum(reply.is_pure for reply in replies)
    met = pure >= MIN_PURE_SHARE * len(replies)
    result = BenchmarkResult(
        "adherence", code, None, get_settings().ollama_model, pure, len(replies), THRESHOLD, met,
        review_sheet=str(sheet),
    )  # fmt: skip
    record_benchmark(directory, result, _section(result, len(rows)))
    return result


def _section(result: BenchmarkResult, flagged: int) -> str:
    verdict = "met" if result.met else "missed"
    return (
        "## Adherence (006 SC-002)\n\n"
        f"Replies with no flagged word: {result.passed}/{result.total} "
        f"({result.passed / result.total:.0%}) against {THRESHOLD}: {verdict}.\n"
        f"Model: {result.model}. {flagged} flagged replies await a verdict in the review sheet.\n"
    )


@pytest.mark.parametrize("code", bench_languages())
def test_replies_stay_in_the_practice_language(code, capsys) -> None:
    player = ScriptedPlayer(code)
    turns = evaluation_set(code).turns
    replies = [reply for scenario, lines in turns.items() for reply in player.play(scenario, lines)]
    result = _record(code, replies)

    with capsys.disabled():
        figure = f"{result.passed}/{result.total}"
        print(f"\n{code} adherence: {figure} replies with no flagged word")  # noqa: T201
        print(f"Review sheet: {result.review_sheet}")  # noqa: T201

    assert result.met
