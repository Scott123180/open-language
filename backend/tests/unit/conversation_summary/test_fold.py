"""T076: long transcripts are summarised in chunks, each under the budget (research R13)."""

import json

from app.conversation_levels import ConversationLevel
from app.conversation_summary.services.storage import StoredSummary, SummaryStorage
from app.conversation_summary.services.summariser import (
    SUMMARY_CHUNK_CHARACTERS,
    Summariser,
    SummaryLine,
    SummaryRequest,
)
from app.practice_languages import ConversationLanguages
from app.services.llm.base import ChatMessage, StructuredLLMProvider

SPANISH = ConversationLanguages.of("es", "en")
POINTS = {
    "points": [{"conversation_language": "Hablan de comida.", "english": "They talk about food."}]
}


class RecordingStructuredLLM(StructuredLLMProvider):
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def chat_json(self, messages: list[ChatMessage], schema: dict) -> str:
        self.prompts.append(messages[-1].content)
        return json.dumps(POINTS)


class MemorySummaries(SummaryStorage):
    def __init__(self, stored: StoredSummary | None = None) -> None:
        self.stored = stored

    def get_latest(self, conversation_id: int) -> StoredSummary | None:
        return self.stored

    def save(self, summary: StoredSummary) -> None:
        self.stored = summary


def _lines(count: int, length: int = 60) -> tuple[SummaryLine, ...]:
    return tuple(
        SummaryLine(index + 1, "user" if index % 2 else "assistant", "x" * length)
        for index in range(count)
    )


def _summarise(llm, lines, storage=None):
    request = SummaryRequest(57, lines, SPANISH, ConversationLevel.NATURAL)
    return Summariser(llm, storage or MemorySummaries(), speaker_names=None).summarise(request)


def test_a_short_transcript_is_one_call():
    llm = RecordingStructuredLLM()

    _summarise(llm, _lines(10))

    assert len(llm.prompts) == 1


def test_a_long_transcript_is_folded_in_chunks_under_the_budget():
    llm = RecordingStructuredLLM()

    _summarise(llm, _lines(400, length=100))

    assert len(llm.prompts) > 1
    assert all(len(prompt) <= SUMMARY_CHUNK_CHARACTERS + 3000 for prompt in llm.prompts)
    assert all("They talk about food." in prompt for prompt in llm.prompts[1:])


def test_a_cached_summary_folds_in_only_the_new_lines():
    llm = RecordingStructuredLLM()
    cached = StoredSummary(57, up_to_message_id=10, level="natural", points=_points())
    lines = _lines(12)

    _summarise(llm, lines, MemorySummaries(cached))

    [prompt] = llm.prompts
    assert "They talk about food." in prompt
    assert prompt.count("x" * 60) == 2


def _points():
    from app.conversation_summary.services.summariser import SummaryPoint

    return (SummaryPoint("Hablan de comida.", "They talk about food."),)
