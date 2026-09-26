"""T036: chat routes run on conversation sessions that stay live between turns."""

import datetime
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.corrections.services.sqlite_storage import SQLiteCorrectionStorageProvider
from app.corrections.services.strategies import NULL_TURN_PLAN, CorrectionStrategy, TurnPlan
from app.main import app
from app.services.factory import (
    get_app_settings,
    get_correction_storage,
    get_correction_strategy,
    get_helper_sessions,
    get_scenario_provider,
    get_session_provider,
    get_storage,
    get_tts,
)
from app.services.helper_sessions import HelperSessionStore
from app.services.llm.base import LLMError
from app.services.llm.selection_types import LLMSelection
from app.services.scenario.static import StaticScenarioProvider
from app.services.storage.base import AppSettingsRecord
from app.services.storage.sqlite import SQLiteStorageProvider
from app.services.tts.base import TTSProvider
from tests.integration.conftest import make_test_session
from tests.support.engine_overrides import install_session_provider
from tests.support.recording_session_provider import RecordingSessionProvider

_SETTINGS = AppSettingsRecord(
    llm_model="llama3.1",
    target_language="es",
    native_language="en",
    tts_voice="es_ES-mls-medium",
    suggestion_count=1,
    whisper_model="base",
    updated_at=datetime.datetime.now(datetime.UTC),
)
GENTLE_SUFFIX = " Recast any mistake naturally."
_WAIT_SECONDS = 2.0


class SilentTTS(TTSProvider):
    @property
    def voice_name(self) -> str:
        return "silent"

    def synthesize(self, text: str, output_path: Path) -> None:
        """Nothing to hear in these tests."""


class ScriptedStrategy(CorrectionStrategy):
    """Returns the queued plans in order, then the null plan."""

    def __init__(self) -> None:
        self.plans: list[TurnPlan] = []

    async def plan_turn(self, context) -> TurnPlan:
        return self.plans.pop(0) if self.plans else NULL_TURN_PLAN


class Harness:
    def __init__(self, client, provider, engine, strategy) -> None:
        self.client = client
        self.provider = provider
        self.engine = engine
        self.strategy = strategy

    def new_conversation(self) -> int:
        response = self.client.post("/api/conversations", json={"scenario_id": "buy-train-ticket"})
        return response.json()["id"]

    def open(self, conversation_id: int) -> list[dict]:
        return self._stream(f"/api/chat/{conversation_id}/open", None)

    def send(self, conversation_id: int, content: str) -> list[dict]:
        body = {"content": content, "input_source": "keyboard"}
        return self._stream(f"/api/chat/{conversation_id}/message", body)

    def ask_helper(self, message: str, helper_session_id: str = "helper-1") -> list[dict]:
        body = {
            "message": message,
            "helper_session_id": helper_session_id,
            "target_language": "Spanish",
            "native_language": "English",
        }
        return self._stream("/api/chat/helper", body)

    def _stream(self, url: str, body: dict | None) -> list[dict]:
        with self.client.stream("POST", url, json=body) as response:
            response.read()
            return [
                json.loads(line[len("data: ") :])
                for line in response.text.splitlines()
                if line.startswith("data: ")
            ]


def _per_request_sessions(tmp_path: Path, opened: list):
    """Storage is handed out per request, as in production: the background TTS thread
    outlives its request, so one shared SQLAlchemy session would collide with the next."""
    db_file = tmp_path / "sessions.db"
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


def _install_chat_overrides(new_session, strategy: ScriptedStrategy) -> None:
    helper_store = HelperSessionStore()
    app.dependency_overrides[get_scenario_provider] = lambda: StaticScenarioProvider()
    app.dependency_overrides[get_storage] = lambda: SQLiteStorageProvider(new_session())
    app.dependency_overrides[get_app_settings] = lambda: _SETTINGS
    app.dependency_overrides[get_tts] = SilentTTS
    app.dependency_overrides[get_correction_strategy] = lambda: strategy
    app.dependency_overrides[get_correction_storage] = lambda: SQLiteCorrectionStorageProvider(
        new_session()
    )
    app.dependency_overrides[get_helper_sessions] = lambda: helper_store


@pytest.fixture()
def harness(tmp_path: Path):
    opened: list = []
    provider = RecordingSessionProvider()
    strategy = ScriptedStrategy()
    conversation_engine = install_session_provider(app, provider)
    _install_chat_overrides(_per_request_sessions(tmp_path, opened), strategy)
    with TestClient(app) as client:
        yield Harness(client, provider, conversation_engine, strategy)
    app.dependency_overrides.clear()
    for session in opened:
        session.close()


def _wait_until(condition) -> None:
    deadline = time.monotonic() + _WAIT_SECONDS
    while not condition():
        assert time.monotonic() < deadline, "condition never became true"
        time.sleep(0.01)


def _pending_ids(session) -> list[list[str]]:
    return [[turn.turn_id for turn in pending] for pending, _ in session.replies]


class TestRoleplayTurns:
    def test_consecutive_turns_reuse_one_session(self, harness):
        conversation_id = harness.new_conversation()
        harness.open(conversation_id)

        harness.send(conversation_id, "Hola")
        harness.send(conversation_id, "Un billete")

        [session] = harness.provider.opened
        assert len(session.replies) == 2
        assert [turn.content for turn in session.replies[1][0]] == ["Un billete"]

    def test_the_opening_line_is_acknowledged_under_its_saved_id(self, harness):
        conversation_id = harness.new_conversation()

        events = harness.open(conversation_id)

        assert harness.provider.opened[0].acknowledged == [f"m{events[-1]['message_id']}"]

    def test_after_a_pool_reset_the_next_turn_rebuilds_with_one_generation(self, harness):
        conversation_id = harness.new_conversation()
        harness.open(conversation_id)
        harness.send(conversation_id, "Hola")
        replies_before = harness.provider.reply_count

        harness.engine.close()
        harness.send(conversation_id, "Un billete")

        rebuilt = harness.provider.opened[-1]
        assert len(harness.provider.opened) == 2
        assert harness.provider.reply_count == replies_before + 1
        assert [turn.role for turn in rebuilt.history] == ["assistant", "user", "assistant"]

    def test_strict_pause_then_retry_reuses_session_with_merged_pending_turns(self, harness):
        conversation_id = harness.new_conversation()
        harness.open(conversation_id)
        harness.strategy.plans = [TurnPlan(generate_reply=False), NULL_TURN_PLAN]

        paused = harness.send(conversation_id, "Yo es cansado")
        harness.send(conversation_id, "Yo estoy cansado")

        [session] = harness.provider.opened
        assert paused[-1] == {"done": True, "message_id": None}
        [(pending, _guidance)] = session.replies
        assert [turn.content for turn in pending] == ["Yo es cansado", "Yo estoy cansado"]

    def test_gentle_guidance_reaches_only_its_own_turn(self, harness):
        conversation_id = harness.new_conversation()
        harness.open(conversation_id)
        harness.strategy.plans = [TurnPlan(reply_prompt_suffix=GENTLE_SUFFIX)]

        harness.send(conversation_id, "Yo es cansado")
        harness.send(conversation_id, "Gracias")

        [session] = harness.provider.opened
        assert [guidance for _, guidance in session.replies] == [GENTLE_SUFFIX, None]


class TestWarmEndpoint:
    def test_warming_is_scheduled_once_then_reported_live(self, harness):
        conversation_id = harness.new_conversation()

        first = harness.client.post(f"/api/chat/{conversation_id}/session")
        _wait_until(lambda: harness.provider.opened and harness.provider.opened[0].warm_count)
        second = harness.client.post(f"/api/chat/{conversation_id}/session")

        assert (first.status_code, first.json()) == (202, {"status": "warming"})
        assert (second.status_code, second.json()) == (202, {"status": "live"})
        assert [session.warm_count for session in harness.provider.opened] == [1]

    def test_unknown_conversation_is_404(self, harness):
        response = harness.client.post("/api/chat/99999/session")

        assert (response.status_code, response.json()) == (
            404,
            {"detail": "Conversation not found"},
        )

    def test_completed_conversation_is_409(self, harness):
        conversation_id = harness.new_conversation()
        harness.client.patch(f"/api/conversations/{conversation_id}", json={"status": "completed"})

        response = harness.client.post(f"/api/chat/{conversation_id}/session")

        assert (response.status_code, response.json()) == (
            409,
            {"detail": "This conversation has ended."},
        )

    def test_a_failed_warm_up_is_never_reported(self, harness):
        conversation_id = harness.new_conversation()
        harness.provider.open_session = _raise_on_open

        response = harness.client.post(f"/api/chat/{conversation_id}/session")

        assert (response.status_code, response.json()) == (202, {"status": "warming"})


def _raise_on_open(key, standing_prompt, history):
    raise LLMError("claude is not signed in", can_retry=False)


def test_completing_a_conversation_closes_its_session(harness):
    conversation_id = harness.new_conversation()
    harness.open(conversation_id)

    harness.client.patch(f"/api/conversations/{conversation_id}", json={"status": "completed"})

    assert harness.provider.opened[0].is_closed


class TestHelperTurns:
    def test_helper_turns_reuse_a_session_keyed_by_helper_id(self, harness):
        harness.ask_helper("How do I say hello?")
        harness.ask_helper("And goodbye?")

        [session] = harness.provider.opened
        assert _pending_ids(session) == [["h0"], ["h2"]]
        assert session.acknowledged == ["h1", "h3"]

    def test_the_helper_is_never_warmed_in_advance(self, harness):
        harness.ask_helper("How do I say hello?")

        assert harness.provider.opened[0].warm_count == 0


class TestSwitchingMidConversation:
    """T069: a changed provider or effort rebuilds the session from saved history."""

    @pytest.fixture()
    def switchable(self, harness):
        providers = {"ollama": harness.provider, "claude": RecordingSessionProvider()}
        providers["claude"].selection = LLMSelection("claude", "sonnet")
        providers["claude"].effort = "low"
        current = {"id": "ollama"}
        app.dependency_overrides[get_session_provider] = lambda: providers[current["id"]]
        return providers, current

    def test_switching_provider_rebuilds_with_the_full_saved_history(self, harness, switchable):
        providers, current = switchable
        conversation_id = harness.new_conversation()
        harness.open(conversation_id)
        harness.send(conversation_id, "Hola")

        current["id"] = "claude"
        harness.send(conversation_id, "Un billete")

        [rebuilt] = providers["claude"].opened
        assert [turn.role for turn in rebuilt.history] == ["assistant", "user", "assistant"]
        assert [[t.content for t in pending] for pending, _ in rebuilt.replies] == [["Un billete"]]
        assert providers["ollama"].opened[0].is_closed

    def test_changing_only_effort_rebuilds(self, harness, switchable):
        providers, current = switchable
        current["id"] = "claude"
        conversation_id = harness.new_conversation()
        harness.open(conversation_id)

        providers["claude"].effort = "high"
        harness.send(conversation_id, "Hola")

        assert len(providers["claude"].opened) == 2
        assert providers["claude"].opened[0].is_closed
