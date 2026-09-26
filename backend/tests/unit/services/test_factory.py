"""T020: every language-model dependency is served by the provider registry."""

from datetime import UTC, datetime

import pytest

from app.services import factory
from app.services.llm.selection_types import LLMSelection
from app.services.storage.base import AppSettingsRecord

_RECORD = AppSettingsRecord(
    llm_model="haiku",
    target_language="es",
    native_language="en",
    tts_voice="es_ES-davefx-medium",
    suggestion_count=1,
    whisper_model="base",
    updated_at=datetime.now(UTC),
    llm_provider="claude",
    llm_effort="medium",
)


@pytest.fixture()
def registry_calls(monkeypatch) -> list[tuple]:
    calls: list[tuple] = []
    built = object()

    def fake_build(selection, settings, effort):
        calls.append((selection, settings, effort))
        return built

    monkeypatch.setattr(factory, "build_llm_provider", fake_build)
    return calls


@pytest.mark.parametrize("dependency", ["get_llm", "get_structured_llm", "get_session_provider"])
def test_dependency_delegates_to_the_registry(registry_calls, dependency):
    getattr(factory, dependency)(_RECORD)

    [(selection, settings, effort)] = registry_calls
    assert selection == LLMSelection("claude", "haiku")
    assert effort == "medium"
    assert settings is factory.get_settings()
