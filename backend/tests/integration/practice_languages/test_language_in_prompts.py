"""T041: every prompt names the conversation's language, never its code (contracts §5, R2)."""

import re

import pytest

from app.services.conversation import SessionKind
from app.services.scenario.static import StaticScenarioProvider
from tests.integration.conversation_levels.level_harness import wait_until
from tests.integration.practice_languages.language_harness import language_harness

LANGUAGE_CODE = re.compile(r"\b(de|es|en)\b")
LOW_CONFIDENCE = 0.1
LEARNER_TEXT = {"de": "Ich haben Hunger heute", "es": "Yo tener hambre hoy"}
NAMES = {"de": "German", "es": "Spanish"}


@pytest.fixture
def harness(tmp_path, monkeypatch):
    yield from language_harness(tmp_path, monkeypatch)


def _conversation_in(harness, code: str, scenario_id: str | None = None) -> int:
    harness.put_settings(target_language=code)
    if scenario_id is None:
        return harness.new_conversation()
    return harness.new_conversation(scenario_id)


def _assert_names(prompt: str, code: str) -> None:
    assert NAMES[code] in prompt
    assert "English" in prompt
    assert not LANGUAGE_CODE.search(prompt), LANGUAGE_CODE.search(prompt)


def _warm(harness, conversation_id: int) -> str:
    assert harness.warm(conversation_id) == {"status": "warming"}
    wait_until(lambda: harness.engine.warmed_prompts)
    return harness.engine.warmed_prompts[-1]


def _roleplay_prompts(harness) -> list[str]:
    requests = harness.engine.requests_of(SessionKind.ROLEPLAY)
    return [r.standing_prompt for r in requests] + harness.engine.warmed_prompts


@pytest.mark.parametrize("code", ["de", "es"])
def test_the_roleplay_prompt_names_the_language_on_open_message_and_warm_up(harness, code):
    conversation_id = _conversation_in(harness, code)

    _warm(harness, conversation_id)
    harness.open(conversation_id)
    harness.send(conversation_id, LEARNER_TEXT[code])

    prompts = _roleplay_prompts(harness)
    assert len(prompts) == 3
    for prompt in prompts:
        _assert_names(prompt, code)


@pytest.mark.parametrize("code", ["de", "es"])
def test_the_opening_instruction_names_the_language(harness, code):
    conversation_id = _conversation_in(harness, code)

    harness.open(conversation_id)

    [opening] = harness.engine.requests_of(SessionKind.ROLEPLAY)
    assert opening.opening_instruction == f"Begin the conversation in {NAMES[code]}."


@pytest.mark.parametrize("code", ["de", "es"])
def test_the_suggestion_prompt_names_the_language(harness, code):
    conversation_id = _conversation_in(harness, code)
    harness.open(conversation_id)

    harness.client.post(f"/api/chat/{conversation_id}/suggestions")

    assert NAMES[code] in harness.llm.prompts[-1]
    assert not LANGUAGE_CODE.search(harness.llm.prompts[-1])


LEARNING_TOOLS = {
    "grammar": lambda message_id: {"message_id": message_id, "content": "Guten Tag"},
    "translate": lambda message_id: {"message_id": message_id, "content": "Guten Tag"},
    "phrasing": lambda message_id: {"message_id": message_id, "content": "Guten Tag"},
    "word-lookup": lambda message_id: {
        "message_id": message_id,
        "selection": "Tag",
        "sentence_context": "Guten Tag",
    },
}
NAMED_BY_TOOL = {
    "grammar": ("English",),
    "translate": ("English",),
    "phrasing": ("German",),
    "word-lookup": ("German", "English"),
}


@pytest.mark.parametrize("tool", list(LEARNING_TOOLS))
def test_each_learning_tool_prompt_names_the_conversation_languages(harness, tool):
    conversation_id = _conversation_in(harness, "de")
    harness.open(conversation_id)
    message_id = harness.last_message_id(conversation_id)

    response = harness.client.post(f"/api/learning/{tool}", json=LEARNING_TOOLS[tool](message_id))

    assert response.status_code == 200, response.text
    prompt = harness.llm.prompts[-1]
    assert all(name in prompt for name in NAMED_BY_TOOL[tool])
    assert not LANGUAGE_CODE.search(prompt)


def test_the_helper_prompt_names_the_conversation_languages(harness):
    conversation_id = _conversation_in(harness, "de")

    harness.ask_helper(conversation_id, "How do I say 'I am hungry'?")

    [request] = harness.engine.requests_of(SessionKind.HELPER)
    _assert_names(request.standing_prompt, "de")


@pytest.mark.parametrize("mode", ["gentle", "strict"])
def test_the_correction_evaluation_prompt_names_the_language(harness, mode):
    harness.put_settings(correction_mode=mode)
    conversation_id = _conversation_in(harness, "de")
    harness.open(conversation_id)

    harness.send(conversation_id, LEARNER_TEXT["de"])

    [prompt] = harness.structured.prompts
    _assert_names(prompt, "de")


def test_the_gentle_recast_names_the_language(harness):
    harness.put_settings(correction_mode="gentle")
    conversation_id = _conversation_in(harness, "de")
    harness.open(conversation_id)

    harness.send(conversation_id, LEARNER_TEXT["de"])

    reply = harness.engine.requests_of(SessionKind.ROLEPLAY)[-1]
    assert "Every word of your reply stays in German." in reply.guidance


@pytest.mark.parametrize("code", ["de", "es"])
def test_the_strict_repeat_request_names_the_language(harness, code):
    harness.put_settings(correction_mode="strict")
    conversation_id = _conversation_in(harness, code)
    harness.open(conversation_id)

    frames = harness.send(
        conversation_id,
        LEARNER_TEXT[code],
        input_source="voice",
        transcription_confidence=LOW_CONFIDENCE,
    )

    [feedback] = [frame for frame in frames if frame.get("event") == "feedback"]
    assert feedback["notes"][0]["explanation"].endswith(f"speak clearly in {NAMES[code]}.")


@pytest.mark.parametrize("scenario", StaticScenarioProvider().get_all(), ids=lambda s: s.id)
def test_every_scenario_names_german_in_a_german_conversation(harness, scenario):
    conversation_id = _conversation_in(harness, "de", scenario.id)

    _assert_names(_warm(harness, conversation_id), "de")


def test_the_german_evaluation_prompt_allows_regional_german_and_capitalisation(harness):
    harness.put_settings(correction_mode="strict")
    conversation_id = _conversation_in(harness, "de")
    harness.open(conversation_id)

    harness.send(conversation_id, LEARNER_TEXT["de"])

    [prompt] = harness.structured.prompts
    never_report = prompt.split("Never report any of the following:")[1].split("\n\n")[0]
    assert "valid in some region where German is spoken" in never_report
    assert "capitalisation" in never_report
