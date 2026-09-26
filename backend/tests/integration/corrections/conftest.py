"""Shared fixtures for the corrections integration tests."""

import datetime
import json
import struct
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.corrections.services.sqlite_storage import SQLiteCorrectionStorageProvider
from app.corrections.services.strategies import CorrectionStrategy, TurnContext, TurnPlan
from app.main import app
from app.services.factory import (
    get_app_settings,
    get_correction_storage,
    get_llm,
    get_scenario_provider,
    get_storage,
    get_tts,
)
from app.services.llm.base import ChatMessage, LLMProvider
from app.services.scenario.static import StaticScenarioProvider
from app.services.storage.base import AppSettingsRecord
from app.services.storage.sqlite import SQLiteStorageProvider
from app.services.tts.base import TTSProvider
from tests.integration.conftest import make_test_session
from tests.support.engine_overrides import override_conversation_engine


def _enable_foreign_keys(dbapi_conn, _record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


VALID_SCENARIO_ID = "buy-train-ticket"
REPLY_TOKENS = ["Buenos", " días"]


def settings_with_mode(mode: str) -> AppSettingsRecord:
    return AppSettingsRecord(
        llm_model="llama3.1",
        target_language="Spanish",
        native_language="English",
        tts_voice="es_ES-mls-medium",
        suggestion_count=3,
        whisper_model="base",
        updated_at=datetime.datetime.now(datetime.UTC),
        correction_mode=mode,
    )


class RecordingLLMProvider(LLMProvider):
    """Counts every streaming call so SC-002's "exactly one call" is assertable."""

    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens
        self.stream_calls: list[list[ChatMessage]] = []

    @property
    def model_name(self) -> str:
        return "stub-model"

    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        self.stream_calls.append(list(messages))
        yield from self._tokens

    def chat(self, messages: list[ChatMessage]) -> str:
        return "".join(self._tokens)


class StubTTSProvider(TTSProvider):
    def __init__(self, tmp_path: Path) -> None:
        self._tmp_path = tmp_path

    @property
    def voice_name(self) -> str:
        return "stub-voice"

    def synthesize(self, text: str, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        header = (
            b"RIFF"
            + struct.pack("<I", 36)
            + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, 16000, 32000, 2, 16)
            + b"data"
            + struct.pack("<I", 0)
        )
        output_path.write_bytes(header)


def build_strict_harness(make_harness, findings, attempts: int = 0):
    """A harness running the real Strict strategy over a scripted evaluator."""
    from app.corrections.services.evaluator import CorrectionEvaluator
    from app.corrections.services.pause_tracker import CorrectionPauseTracker
    from app.corrections.services.strategies import StrictCorrectionStrategy

    class ScriptedEvaluator(CorrectionEvaluator):
        def __init__(self, findings) -> None:
            self.findings = findings
            self.calls = []

        def evaluate(self, request):
            self.calls.append(request)
            return self.findings

    harness = make_harness(mode="strict")
    evaluator = ScriptedEvaluator(findings)
    strategy = StrictCorrectionStrategy(
        evaluator, CorrectionPauseTracker(harness.correction_storage)
    )
    _override_strategy(strategy)
    harness.evaluator = evaluator
    return harness


def build_gentle_harness(make_harness, findings):
    """A harness running the real Gentle strategy over a scripted evaluator."""
    from app.corrections.services.evaluator import CorrectionEvaluator
    from app.corrections.services.strategies import GentleCorrectionStrategy

    class ScriptedEvaluator(CorrectionEvaluator):
        def __init__(self, findings) -> None:
            self.findings = findings
            self.calls = []

        def evaluate(self, request):
            self.calls.append(request)
            return self.findings

    harness = make_harness(mode="gentle")
    evaluator = ScriptedEvaluator(findings)
    _override_strategy(GentleCorrectionStrategy(evaluator))
    harness.evaluator = evaluator
    return harness


def _override_strategy(strategy) -> None:
    from app.services.factory import get_correction_strategy

    app.dependency_overrides[get_correction_strategy] = lambda: strategy


class StubStrategy(CorrectionStrategy):
    """A strategy whose plan is fixed by the test, not derived from a mode."""

    def __init__(self, plan: TurnPlan) -> None:
        self._plan = plan
        self.contexts: list[TurnContext] = []

    async def plan_turn(self, context: TurnContext) -> TurnPlan:
        self.contexts.append(context)
        return self._plan


class CorrectionsHarness:
    """Everything a corrections integration test needs to drive one turn.

    Storage is handed out per access, mirroring the per-request session the real
    dependency graph creates: a single shared session would let the background
    TTS thread collide with the next request's commit.
    """

    def __init__(self, client: TestClient, assertion_session: Session, llm) -> None:
        self.client = client
        self._assertion_session = assertion_session
        self.llm = llm

    def _fresh(self) -> Session:
        """End the open read transaction so commits from request sessions are visible."""
        self._assertion_session.rollback()
        return self._assertion_session

    @property
    def storage(self):
        return SQLiteStorageProvider(self._fresh())

    @property
    def correction_storage(self):
        return SQLiteCorrectionStorageProvider(self._fresh())

    def create_conversation(self) -> int:
        response = self.client.post("/api/conversations", json={"scenario_id": VALID_SCENARIO_ID})
        assert response.status_code == 201
        return response.json()["id"]

    def send(self, conversation_id: int, content: str, **body) -> list[dict]:
        payload = {"content": content, "input_source": "keyboard", **body}
        with self.client.stream(
            "POST",
            f"/api/chat/{conversation_id}/message",
            json=payload,
        ) as response:
            assert response.status_code == 200
            response.read()
            raw = response.text
        return parse_sse(raw)

    def post_message(self, conversation_id: int, content: str, **body):
        return self.client.post(
            f"/api/chat/{conversation_id}/message",
            json={"content": content, "input_source": "keyboard", **body},
        )


def parse_sse(raw_text: str) -> list[dict]:
    return [
        json.loads(line[len("data: ") :])
        for line in raw_text.splitlines()
        if line.startswith("data: ")
    ]


class _RequestSessions:
    """Hands out one SQLAlchemy session per request, all closed at teardown.

    NullPool so each session owns its connection: the background TTS thread outlives the
    request that created its session, and a pooled connection returned underneath it would be
    reused while still in use.
    """

    def __init__(self, db_file: Path, opened: list[Session]) -> None:
        engine = create_engine(
            f"sqlite:///{db_file}",
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
        )
        event.listen(engine, "connect", _enable_foreign_keys)
        self._session_maker = sessionmaker(bind=engine)
        self._opened = opened

    def new_session(self) -> Session:
        session = self._session_maker()
        self._opened.append(session)
        return session


def _install_overrides(mode: str, requests: _RequestSessions, llm, tmp_path: Path) -> None:
    app.dependency_overrides[get_scenario_provider] = lambda: StaticScenarioProvider()
    app.dependency_overrides[get_storage] = lambda: SQLiteStorageProvider(requests.new_session())
    app.dependency_overrides[get_correction_storage] = lambda: SQLiteCorrectionStorageProvider(
        requests.new_session()
    )
    app.dependency_overrides[get_app_settings] = lambda: settings_with_mode(mode)
    app.dependency_overrides[get_llm] = lambda: llm
    override_conversation_engine(app, llm)
    app.dependency_overrides[get_tts] = lambda: StubTTSProvider(tmp_path=tmp_path)


class _HarnessFactory:
    """Builds harnesses for a given correction mode, and tears every one of them down."""

    def __init__(self, tmp_path: Path) -> None:
        self._tmp_path = tmp_path
        self._clients: list[TestClient] = []
        self._sessions: list[Session] = []

    def __call__(
        self, mode: str = "off", strategy: CorrectionStrategy | None = None
    ) -> CorrectionsHarness:
        from app.services.factory import get_correction_strategy

        db_file = self._tmp_path / f"test-{len(self._clients)}.db"
        assertion_session, pooled_engine = make_test_session(str(db_file))
        self._sessions.append(assertion_session)
        requests = _RequestSessions(db_file, self._sessions)
        pooled_engine.dispose()
        llm = RecordingLLMProvider(tokens=list(REPLY_TOKENS))
        _install_overrides(mode, requests, llm, self._tmp_path)
        if strategy is not None:
            app.dependency_overrides[get_correction_strategy] = lambda: strategy
        client = TestClient(app)
        client.__enter__()
        self._clients.append(client)
        return CorrectionsHarness(client, assertion_session, llm)

    def close(self) -> None:
        for client in self._clients:
            client.__exit__(None, None, None)
        app.dependency_overrides.clear()
        for session in self._sessions:
            session.close()


@pytest.fixture
def make_harness(tmp_path: Path):
    """Build a harness for a given correction mode and optional strategy override."""
    factory = _HarnessFactory(tmp_path)
    yield factory
    factory.close()
