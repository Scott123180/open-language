"""SC-002 German adherence benchmark against the real default local model (research R8).

Deselected by default (`-m "not benchmark"` in pyproject), so CI stays hermetic. Run it by hand
from `backend/` and record the printed figure, then give each flagged reply a human verdict in the
review sheet it writes:

    backend/.venv/bin/pytest -m benchmark -s \
        tests/integration/practice_languages/test_german_benchmark.py

The figure is printed and the sheet written before the assertion runs, so a missed threshold still
leaves the complete evidence behind (quickstart §3).
"""

import datetime
from dataclasses import dataclass
from pathlib import Path

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
from tests.integration.practice_languages.evaluation_set import evaluation_set
from tests.integration.practice_languages.text_purity import foreign_words
from tests.support.engine_overrides import TEST_IDLE_TTL, TEST_MAX_LIVE

pytestmark = pytest.mark.benchmark

TARGET_LANGUAGE = "de"
NATIVE_LANGUAGE = "en"
SC_002_MIN_PURE_SHARE = 0.95
REVIEW_SHEET = Path(__file__).resolve().parents[4] / "specs" / "006-german-language-support"
REVIEW_SHEET_NAME = "german-review-sheet.md"
GERMAN_TURNS = evaluation_set(TARGET_LANGUAGE).turns


@dataclass(frozen=True, slots=True)
class Reply:
    scenario_id: str
    learner_text: str
    text: str

    @property
    def flagged(self) -> list[str]:
        return foreign_words(self.text)

    @property
    def is_pure_german(self) -> bool:
        """An empty reply is a failure, never a trivially clean one."""
        return bool(self.text.strip()) and not self.flagged


def _conversation(scenario_id: str, conversation_id: int) -> ConversationRecord:
    title = next(s.title for s in StaticScenarioProvider().get_all() if s.id == scenario_id)
    return ConversationRecord(
        id=conversation_id,
        scenario_id=scenario_id,
        scenario_title=title,
        target_language=TARGET_LANGUAGE,
        native_language=NATIVE_LANGUAGE,
        status="active",
        started_at=datetime.datetime.now(datetime.UTC),
        ended_at=None,
        llm_model=get_settings().ollama_model,
    )


class ScriptedPlayer:
    """Plays scripted German learner turns through the real engine and the real default model."""

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

    def play(self, scenario_id: str, turns: tuple[str, ...]) -> list[Reply]:
        self._next_id += 1
        record = _conversation(scenario_id, self._next_id)
        prompt = _standing_roleplay_prompt(
            record, StaticScenarioProvider(), ConversationLevel.NATURAL
        )
        key = SessionKey(SessionKind.ROLEPLAY, str(self._next_id))
        history: list[SavedTurn] = []
        replies = [
            Reply(scenario_id, turn, self._reply(key, prompt, history, turn)) for turn in turns
        ]
        self._engine.end(key)
        return replies

    def _reply(self, key: SessionKey, prompt: str, history: list[SavedTurn], text: str) -> str:
        history.append(SavedTurn(f"u{len(history)}", "user", text))
        request = TurnRequest(key, prompt, tuple(history), None, None)
        reply = "".join(self._engine.stream_turn(self._provider, request)).strip()
        reply_id = f"a{len(history)}"
        self._engine.acknowledge(key, reply_id)
        history.append(SavedTurn(reply_id, "assistant", reply))
        return reply


def _review_row(reply: Reply) -> str:
    cells = (reply.scenario_id, reply.learner_text, reply.text, ", ".join(reply.flagged))
    escaped = (cell.replace("|", "\\|").replace("\n", " ") for cell in cells)
    return "| " + " | ".join(escaped) + " |  |"


def _write_review_sheet(replies: list[Reply], directory: Path) -> Path:
    header = (
        "# German review sheet (SC-002)\n\nEvery reply the purity check flagged. Mark each "
        "`foreign` if it really contains an English or Spanish word, or `German` if the flag was "
        "wrong (a name, or a standard German word).\n\n"
        "| Scenario | Learner | Reply | Flagged words | Verdict |\n|---|---|---|---|---|\n"
    )
    rows = [_review_row(reply) for reply in replies if reply.flagged]
    sheet = directory / REVIEW_SHEET_NAME
    sheet.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    return sheet


def test_german_replies_meet_sc_002(capsys) -> None:
    player = ScriptedPlayer()
    replies = [
        reply for scenario, turns in GERMAN_TURNS.items() for reply in player.play(scenario, turns)
    ]
    pure = sum(reply.is_pure_german for reply in replies)
    sheet = _write_review_sheet(replies, REVIEW_SHEET)

    with capsys.disabled():
        print(f"\nSC-002 replies with no flagged word: {pure}/{len(replies)}")  # noqa: T201
        print(f"Review sheet: {sheet}")  # noqa: T201
        for reply in replies[:3]:
            print(f"  {reply.learner_text} → {reply.text}")  # noqa: T201

    assert pure >= SC_002_MIN_PURE_SHARE * len(replies)
