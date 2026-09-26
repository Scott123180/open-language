"""SC-001 – SC-004 level adherence benchmark against the real default Ollama model (research R9).

Deselected by default (`-m "not benchmark"` in pyproject), so CI stays hermetic. Run it by hand
from `backend/` and record every printed figure, then mark the review sheet it writes:

    backend/.venv/bin/pytest -m benchmark -s \
        tests/integration/conversation_levels/test_level_benchmark.py

Every figure is printed and the sheet written before any assertion runs, so a missed threshold
still leaves the complete evidence behind (quickstart §3).
"""

import datetime
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.config import get_settings
from app.conversation_levels import LEVEL_CATALOG, ConversationLevel
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
from tests.integration.conversation_levels.evaluation_set import (
    EVALUATION_SET,
    REVIEW_QUESTIONS,
    LearnerTurn,
    ScriptedConversation,
)
from tests.integration.conversation_levels.text_metrics import (
    mean_words_per_sentence,
    meets_length_limits,
    native_language_words,
    share_outside,
)
from tests.support.engine_overrides import TEST_IDLE_TTL, TEST_MAX_LIVE

pytestmark = pytest.mark.benchmark

TARGET_LANGUAGE = "es"
NATIVE_LANGUAGE = "en"
SC_BEGINNER_MIN_COMPLIANCE = 0.90
SC_OTHER_MIN_COMPLIANCE = 0.85
VOCABULARY_BAND_FOR_SC_003 = 1500
REVIEW_SHEET_NAME = "level-review-sheet.md"


@dataclass(frozen=True, slots=True)
class Reply:
    level: ConversationLevel
    scenario_id: str
    learner_turn: LearnerTurn
    text: str


def _conversation(scenario: ScriptedConversation, conversation_id: int) -> ConversationRecord:
    title = next(
        s.title for s in StaticScenarioProvider().get_all() if s.id == scenario.scenario_id
    )
    return ConversationRecord(
        id=conversation_id,
        scenario_id=scenario.scenario_id,
        scenario_title=title,
        target_language=TARGET_LANGUAGE,
        native_language=NATIVE_LANGUAGE,
        status="active",
        started_at=datetime.datetime.now(datetime.UTC),
        ended_at=None,
        llm_model=get_settings().ollama_model,
    )


class ScriptedPlayer:
    """Plays scripted learner turns through the real engine and the real default model."""

    def __init__(self) -> None:
        settings = get_settings()
        self._provider = build_llm_provider(
            LLMSelection(DEFAULT_PROVIDER_ID, settings.ollama_model), settings
        )
        pool = ConversationSessionPool(
            TEST_MAX_LIVE, TEST_IDLE_TTL, clock=lambda: datetime.datetime.now(datetime.UTC)
        )
        self._engine = ConversationEngine(pool)
        self._next_id = 0

    def play(self, scenario: ScriptedConversation, level: ConversationLevel) -> list[Reply]:
        self._next_id += 1
        record = _conversation(scenario, self._next_id)
        prompt = _standing_roleplay_prompt(record, StaticScenarioProvider(), level)
        key = SessionKey(SessionKind.ROLEPLAY, str(self._next_id))
        history: list[SavedTurn] = []
        replies = [self._reply(key, prompt, history, turn) for turn in scenario.turns]
        self._engine.end(key)
        return [Reply(level, scenario.scenario_id, turn, text) for turn, text in replies]

    def _reply(self, key, prompt: str, history: list[SavedTurn], turn: LearnerTurn):
        history.append(SavedTurn(f"u{len(history)}", "user", turn.text))
        request = TurnRequest(key, prompt, tuple(history), None, None)
        text = "".join(self._engine.stream_turn(self._provider, request)).strip()
        reply_id = f"a{len(history)}"
        self._engine.acknowledge(key, reply_id)
        history.append(SavedTurn(reply_id, "assistant", text))
        return turn, text


def _collect_replies() -> dict[ConversationLevel, list[Reply]]:
    player = ScriptedPlayer()
    return {
        level: [reply for scenario in EVALUATION_SET for reply in player.play(scenario, level)]
        for level in ConversationLevel
    }


def _length_compliance(replies: list[Reply]) -> int:
    limits = LEVEL_CATALOG[replies[0].level].limits
    assert limits is not None
    return sum(
        meets_length_limits(r.text, limits.max_sentences_per_reply, limits.max_words_per_sentence)
        for r in replies
    )


def _complexity(replies: list[Reply], common_words: frozenset[str]) -> tuple[float, float]:
    texts = [reply.text for reply in replies]
    return mean_words_per_sentence(texts), share_outside(texts, common_words)


def _common_words() -> frozenset[str]:
    from wordfreq import top_n_list

    return frozenset(top_n_list(TARGET_LANGUAGE, VOCABULARY_BAND_FOR_SC_003))


@dataclass(frozen=True, slots=True)
class Figures:
    compliance: dict[ConversationLevel, int]
    complexity: dict[ConversationLevel, tuple[float, float]]
    native_replies: int
    total_per_level: int


def _measure(by_level: dict[ConversationLevel, list[Reply]]) -> Figures:
    common = _common_words()
    limited = [level for level in ConversationLevel if LEVEL_CATALOG[level].limits is not None]
    every_reply = [reply for replies in by_level.values() for reply in replies]
    return Figures(
        compliance={level: _length_compliance(by_level[level]) for level in limited},
        complexity={level: _complexity(by_level[level], common) for level in ConversationLevel},
        native_replies=sum(bool(native_language_words(reply.text)) for reply in every_reply),
        total_per_level=len(by_level[ConversationLevel.NATURAL]),
    )


def _print_figures(figures: Figures) -> None:
    total = figures.total_per_level
    beginner = figures.compliance[ConversationLevel.BEGINNER]
    elementary = figures.compliance[ConversationLevel.ELEMENTARY]
    intermediate = figures.compliance[ConversationLevel.INTERMEDIATE]
    # Printing is the point: these figures are recorded against the spec's success criteria.
    print(f"\nSC-001 Beginner length compliance: {beginner}/{total}")  # noqa: T201
    print(  # noqa: T201
        f"SC-002 Elementary / Intermediate length compliance: "
        f"{elementary}/{total} / {intermediate}/{total}"
    )
    for level, (mean_words, share) in figures.complexity.items():
        print(  # noqa: T201
            f"SC-003 {level.value}: mean words per sentence {mean_words:.2f}, "
            f"share outside top {VOCABULARY_BAND_FOR_SC_003:,} {share:.1%}"
        )
    native = figures.native_replies
    print(f"SC-004 replies containing native-language words: {native}")  # noqa: T201


def _review_row(reply: Reply) -> str:
    limits = LEVEL_CATALOG[reply.level].limits
    tenses = limits.tenses if limits else "any"
    question = REVIEW_QUESTIONS.get(reply.learner_turn.probes or "", "")
    cells = (reply.level.value, reply.scenario_id, reply.learner_turn.text, reply.text, tenses)
    escaped = (cell.replace("|", "\\|").replace("\n", " ") for cell in cells)
    return "| " + " | ".join(escaped) + f" |  | {question} |  |"


def _write_review_sheet(by_level: dict[ConversationLevel, list[Reply]], directory: Path) -> Path:
    header = (
        "# Level review sheet\n\nMark each reply's tenses as `within` or `outside` its level, "
        "and answer the question on tagged rows `yes` or `no`.\n\n"
        "| Level | Scenario | Learner | Reply | Allowed tenses | Within/outside | Question | "
        "Yes/no |\n|---|---|---|---|---|---|---|---|\n"
    )
    rows = [_review_row(reply) for replies in by_level.values() for reply in replies]
    sheet = directory / REVIEW_SHEET_NAME
    sheet.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    return sheet


def _threshold_failures(figures: Figures) -> list[str]:
    total = figures.total_per_level
    minimums = {
        ConversationLevel.BEGINNER: SC_BEGINNER_MIN_COMPLIANCE,
        ConversationLevel.ELEMENTARY: SC_OTHER_MIN_COMPLIANCE,
        ConversationLevel.INTERMEDIATE: SC_OTHER_MIN_COMPLIANCE,
    }
    failures = [
        f"{level.value} length compliance {figures.compliance[level]}/{total} < {minimum:.0%}"
        for level, minimum in minimums.items()
        if figures.compliance[level] < minimum * total
    ]
    if figures.native_replies:
        failures.append(f"{figures.native_replies} replies contain native-language words")
    return failures + _complexity_failures(figures)


def _complexity_failures(figures: Figures) -> list[str]:
    ordered = [figures.complexity[level] for level in ConversationLevel]
    failures = []
    for index, name in enumerate(("mean words per sentence", "share outside the top band")):
        values = [pair[index] for pair in ordered]
        if any(lower >= higher for lower, higher in zip(values, values[1:], strict=False)):
            failures.append(f"SC-003 {name} does not rise strictly: {values}")
    return failures


def test_levels_meet_sc_001_to_sc_004(tmp_path, capsys) -> None:
    by_level = _collect_replies()
    figures = _measure(by_level)
    sheet = _write_review_sheet(by_level, tmp_path)

    with capsys.disabled():
        _print_figures(figures)
        print(f"Review sheet: {sheet}")  # noqa: T201

    failures = _threshold_failures(figures)
    assert not failures, "; ".join(failures)
