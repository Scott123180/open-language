"""A StructuredLLMProvider that answers every summary request with fixed points."""

import json

from app.services.llm.base import ChatMessage, LLMError, StructuredLLMProvider

DEFAULT_POINTS = (
    {"conversation_language": "Hablan de la paella.", "english": "They talk about paella."},
    {
        "conversation_language": "Ahora hablan del precio.",
        "english": "Now they talk about the price.",
    },
)


class ScriptedSummaryLLM(StructuredLLMProvider):
    def __init__(self, points=DEFAULT_POINTS) -> None:
        self.points = list(points)
        self.calls: list[list[ChatMessage]] = []
        self.error: LLMError | None = None
        self.raw_reply: str | None = None

    def chat_json(self, messages: list[ChatMessage], schema: dict) -> str:
        self.calls.append(messages)
        if self.error is not None:
            raise self.error
        return self.raw_reply or json.dumps({"points": self.points})

    @property
    def last_prompt(self) -> str:
        return self.calls[-1][-1].content
