"""A chat app wired for level tests: real settings storage, recorded turns, fake model and TTS.

The level is read from the stored settings exactly as in production (`get_app_settings` is not
overridden), so a `PUT /api/settings` in a test reaches the next request the way a learner's change
would. Every `TurnRequest` the routers hand the engine is recorded, as is every warm-up.
"""

import json
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.conversation_levels import ConversationLevel
from app.corrections.services.sqlite_storage import SQLiteCorrectionStorageProvider
from app.corrections.services.strategies import NULL_TURN_PLAN, CorrectionStrategy, TurnPlan
from app.main import app
from app.practice_languages import ConversationLanguages
from app.prompts.templates import build_roleplay_system_prompt
from app.services.conversation import (
    ConversationEngine,
    SavedTurn,
    SessionCapableProvider,
    SessionKey,
    SessionKind,
    TurnRequest,
)
from app.services.conversation.pool import ConversationSessionPool
from app.services.factory import (
    get_availability_checkers,
    get_conversation_engine,
    get_correction_storage,
    get_correction_strategy,
    get_helper_sessions,
    get_llm,
    get_scenario_provider,
    get_session_provider,
    get_storage,
)
from app.services.helper_sessions import HelperSessionStore
from app.services.llm.availability import AlwaysAvailable
from app.services.llm.base import ChatMessage, LLMProvider
from app.services.scenario.static import StaticScenarioProvider
from app.services.storage.base import ConversationRecord
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.integration.conftest import make_test_session
from tests.support.engine_overrides import TEST_IDLE_TTL, TEST_MAX_LIVE
from tests.support.fake_speech import RecordingTtsBuilder, override_speech
from tests.support.recording_session_provider import RecordingSessionProvider

SCENARIO_ID = "order-at-restaurant"
WAIT_SECONDS = 2.0


class RecordingEngine(ConversationEngine):
    """The real engine, noting each turn request and warm-up prompt it is handed."""

    def __init__(self) -> None:
        pool = ConversationSessionPool(
            TEST_MAX_LIVE, TEST_IDLE_TTL, clock=lambda: datetime.now(UTC)
        )
        super().__init__(pool)
        self.requests: list[TurnRequest] = []
        self.warmed_prompts: list[str] = []

    def stream_turn(self, provider: SessionCapableProvider, request: TurnRequest) -> Iterator[str]:
        self.requests.append(request)
        return super().stream_turn(provider, request)

    def warm(
        self,
        provider: SessionCapableProvider,
        key: SessionKey,
        standing_prompt: str,
        history: Sequence[SavedTurn],
    ) -> None:
        self.warmed_prompts.append(standing_prompt)
        super().warm(provider, key, standing_prompt, history)

    def requests_of(self, kind: SessionKind) -> list[TurnRequest]:
        return [request for request in self.requests if request.key.kind is kind]


class HookedSessionProvider(RecordingSessionProvider):
    """Runs a one-shot callback while the next reply is being produced."""

    def __init__(self) -> None:
        super().__init__()
        self.during_next_reply: Callable[[], None] | None = None

    def wait_if_gated(self) -> None:
        hook, self.during_next_reply = self.during_next_reply, None
        if hook is not None:
            hook()
        super().wait_if_gated()


class CapturingLLM(LLMProvider):
    """Records each prompt sent through `chat` and answers with a fixed numbered list."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def chat(self, messages: list[ChatMessage]) -> str:
        self.prompts.append(messages[-1].content)
        return "1. Hola\n2. Buenas"

    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        yield self.chat(messages)

    @property
    def model_name(self) -> str:
        return "capturing-model"


class FixedStrategy(CorrectionStrategy):
    """Always returns `plan`, so a test can put Gentle-mode guidance on every turn."""

    def __init__(self, plan: TurnPlan = NULL_TURN_PLAN) -> None:
        self.plan = plan

    async def plan_turn(self, context) -> TurnPlan:
        return self.plan


@dataclass
class LevelHarness:
    client: TestClient
    engine: RecordingEngine
    provider: HookedSessionProvider
    llm: CapturingLLM
    strategy: FixedStrategy
    speech: RecordingTtsBuilder
    new_session: Callable[[], object]
    scenarios: StaticScenarioProvider = field(default_factory=StaticScenarioProvider)

    def storage(self) -> SQLiteStorageProvider:
        return SQLiteStorageProvider(self.new_session())

    def set_level(self, level: ConversationLevel) -> None:
        response = self.client.put("/api/settings", json={"conversation_level": level.value})
        assert response.status_code == 200, response.text

    def new_conversation(self, scenario_id: str = SCENARIO_ID) -> int:
        response = self.client.post("/api/conversations", json={"scenario_id": scenario_id})
        return response.json()["id"]

    def new_custom_conversation(self, custom_prompt: str) -> int:
        record = self.storage().create_conversation(
            scenario_id="custom",
            scenario_title="Custom",
            target_language="es",
            native_language="en",
            llm_model="fake-model",
            custom_prompt=custom_prompt,
        )
        return record.id

    def conversation(self, conversation_id: int) -> ConversationRecord:
        record = self.storage().get_conversation(conversation_id)
        assert record is not None
        return record

    def roleplay_prompt(self, conversation_id: int) -> str:
        """What `build_roleplay_system_prompt` gives this conversation, before any level."""
        record = self.conversation(conversation_id)
        if record.custom_prompt:
            description, character = "a custom scenario defined by the user", record.custom_prompt
        else:
            scenario = next(s for s in self.scenarios.get_all() if s.id == record.scenario_id)
            description, character = scenario.description, scenario.ai_context_prompt
        languages = ConversationLanguages.of(record.target_language, record.native_language)
        return build_roleplay_system_prompt(
            scenario_title=record.scenario_title,
            scenario_description=description,
            character_description=character,
            target_language=languages.target_name,
            native_language=languages.native_name,
        )

    def open(self, conversation_id: int) -> list[dict]:
        return self.stream(f"/api/chat/{conversation_id}/open", None)

    def send(self, conversation_id: int, content: str) -> list[dict]:
        body = {"content": content, "input_source": "keyboard"}
        return self.stream(f"/api/chat/{conversation_id}/message", body)

    def warm(self, conversation_id: int) -> dict:
        return self.client.post(f"/api/chat/{conversation_id}/session").json()

    def ask_helper(self, message: str, helper_session_id: str = "helper-1") -> list[dict]:
        """Ask in a new conversation: the helper takes its languages from one (FR-009)."""
        body = {
            "message": message,
            "helper_session_id": helper_session_id,
            "conversation_id": self.new_conversation(),
        }
        return self.stream("/api/chat/helper", body)

    def stream(self, url: str, body: dict | None) -> list[dict]:
        with self.client.stream("POST", url, json=body) as response:
            response.read()
            return [
                json.loads(line.removeprefix("data: "))
                for line in response.text.splitlines()
                if line.startswith("data: ")
            ]


def wait_until(condition: Callable[[], bool]) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    while not condition():
        assert time.monotonic() < deadline, "condition never became true"
        time.sleep(0.01)


def _session_factory(db_file: Path, opened: list) -> Callable[[], object]:
    """A session per request, as in production: background TTS outlives its request."""
    schema_session, schema_engine = make_test_session(str(db_file))
    schema_session.close()
    schema_engine.dispose()
    engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False}, poolclass=NullPool
    )

    def new_session():
        opened.append(sessionmaker(bind=engine)())
        return opened[-1]

    return new_session


def _install_overrides(harness: LevelHarness) -> None:
    helper_store = HelperSessionStore()
    overrides = app.dependency_overrides
    overrides[get_conversation_engine] = lambda: harness.engine
    overrides[get_session_provider] = lambda: harness.provider
    overrides[get_llm] = lambda: harness.llm
    overrides[get_scenario_provider] = lambda: harness.scenarios
    overrides[get_storage] = harness.storage
    overrides[get_correction_strategy] = lambda: harness.strategy
    overrides[get_correction_storage] = lambda: SQLiteCorrectionStorageProvider(
        harness.new_session()
    )
    overrides[get_helper_sessions] = lambda: helper_store
    overrides[get_availability_checkers] = lambda: {
        "ollama": AlwaysAvailable(),
        "claude": AlwaysAvailable(),
    }


def level_harness(tmp_path: Path, monkeypatch) -> Iterator[LevelHarness]:
    """Yield a harness on a fresh database; use from a pytest fixture."""
    opened: list = []
    harness = _new_harness(_session_factory(tmp_path / "levels.db", opened))
    _install_overrides(harness)
    with harness.client:
        yield harness
    app.dependency_overrides.clear()
    for session in opened:
        session.close()


def _new_harness(new_session: Callable[[], object]) -> LevelHarness:
    return LevelHarness(
        TestClient(app),
        RecordingEngine(),
        HookedSessionProvider(),
        CapturingLLM(),
        FixedStrategy(),
        override_speech(app),
        new_session,
    )
