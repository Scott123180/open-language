"""A chat app wired for practice-language tests: real settings, recorded prompts, fake speech.

Settings are read from storage exactly as in production (`get_app_settings` is not overridden),
so `PUT /api/settings` changes the practice language the way a learner would. The correction
strategy is the real one for the stored mode, over a recording structured model, so its
evaluation prompt, recast and repeat request are all observable.
"""

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from fastapi.testclient import TestClient

from app.corrections.services.sqlite_storage import SQLiteCorrectionStorageProvider
from app.main import app
from app.services.factory import (
    get_availability_checkers,
    get_conversation_engine,
    get_correction_storage,
    get_helper_sessions,
    get_llm,
    get_scenario_provider,
    get_session_provider,
    get_storage,
    get_structured_llm,
)
from app.services.helper_sessions import HelperSessionStore
from app.services.llm.availability import AlwaysAvailable
from app.services.llm.base import ChatMessage, StructuredLLMProvider
from app.services.scenario.static import StaticScenarioProvider
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.integration.conversation_levels.level_harness import (
    CapturingLLM,
    HookedSessionProvider,
    RecordingEngine,
    _session_factory,
)
from tests.support.fake_speech import RecordingTtsBuilder, override_speech

SCENARIO_ID = "order-at-restaurant"
FINDING = {
    "verdict": "has_mistakes",
    "corrections": [
        {
            "category": "conjugation",
            "error_fragment": "ich haben",
            "corrected_text": "Ich habe Hunger.",
            "explanation": "With 'ich' the verb is 'habe'.",
        }
    ],
}


class RecordingStructuredLLM(StructuredLLMProvider):
    """Records each evaluation prompt and reports one conjugation mistake."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def chat_json(self, messages: list[ChatMessage], schema: dict) -> str:
        self.prompts.append(messages[-1].content)
        return json.dumps(FINDING)


@dataclass
class LanguageHarness:
    client: TestClient
    engine: RecordingEngine
    llm: CapturingLLM
    structured: RecordingStructuredLLM
    speech: RecordingTtsBuilder
    new_session: Callable[[], object]
    scenarios: StaticScenarioProvider = field(default_factory=StaticScenarioProvider)

    def storage(self) -> SQLiteStorageProvider:
        return SQLiteStorageProvider(self.new_session())

    def put_settings(self, **body) -> dict:
        response = self.client.put("/api/settings", json=body)
        assert response.status_code == 200, response.text
        return response.json()

    def new_conversation(self, scenario_id: str = SCENARIO_ID) -> int:
        response = self.client.post("/api/conversations", json={"scenario_id": scenario_id})
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def open(self, conversation_id: int) -> list[dict]:
        return self.stream(f"/api/chat/{conversation_id}/open", None)

    def send(self, conversation_id: int, content: str, **body) -> list[dict]:
        payload = {"content": content, "input_source": "keyboard", **body}
        return self.stream(f"/api/chat/{conversation_id}/message", payload)

    def warm(self, conversation_id: int) -> dict:
        return self.client.post(f"/api/chat/{conversation_id}/session").json()

    def ask_helper(self, conversation_id: int, message: str) -> list[dict]:
        body = {
            "message": message,
            "helper_session_id": "helper-1",
            "conversation_id": conversation_id,
        }
        return self.stream("/api/chat/helper", body)

    def last_message_id(self, conversation_id: int) -> int:
        return self.storage().get_messages(conversation_id)[-1].id

    def stream(self, url: str, body: dict | None) -> list[dict]:
        with self.client.stream("POST", url, json=body) as response:
            response.read()
            return [
                json.loads(line.removeprefix("data: "))
                for line in response.text.splitlines()
                if line.startswith("data: ")
            ]


def language_harness(tmp_path: Path, monkeypatch) -> Iterator[LanguageHarness]:
    """Yield a harness on a fresh database; use from a pytest fixture."""
    opened: list = []
    harness = LanguageHarness(
        TestClient(app),
        RecordingEngine(),
        CapturingLLM(),
        RecordingStructuredLLM(),
        override_speech(app),
        _session_factory(tmp_path / "languages.db", opened),
    )
    _install_overrides(harness)
    with harness.client:
        yield harness
    app.dependency_overrides.clear()
    for session in opened:
        session.close()


def _install_overrides(harness: LanguageHarness) -> None:
    helper_store = HelperSessionStore()
    provider = HookedSessionProvider()
    overrides = app.dependency_overrides
    overrides[get_conversation_engine] = lambda: harness.engine
    overrides[get_session_provider] = lambda: provider
    overrides[get_llm] = lambda: harness.llm
    overrides[get_structured_llm] = lambda: harness.structured
    overrides[get_scenario_provider] = lambda: harness.scenarios
    overrides[get_storage] = harness.storage
    overrides[get_correction_storage] = lambda: SQLiteCorrectionStorageProvider(
        harness.new_session()
    )
    overrides[get_helper_sessions] = lambda: helper_store
    overrides[get_availability_checkers] = lambda: {
        "ollama": AlwaysAvailable(),
        "claude": AlwaysAvailable(),
    }
