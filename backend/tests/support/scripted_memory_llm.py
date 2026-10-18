"""A StructuredLLMProvider that answers memory and discovery requests from a queue.

Each call takes the next queued reply: a dict (sent as JSON), a raw string, or an `LLMError` to
raise. With the queue empty it answers with `default`. It records every prompt and schema, and
can hold every call behind a gate, for the timeout tests.
"""

import json
import threading

from app.services.llm.base import ChatMessage, LLMError, StructuredLLMProvider

EMPTY_MEMORY = {"topic": None, "about_learner": []}


class ScriptedMemoryLLM(StructuredLLMProvider):
    def __init__(self, default: dict | str = EMPTY_MEMORY) -> None:
        self.default = default
        self._queue: list[dict | str | LLMError] = []
        self.calls: list[list[ChatMessage]] = []
        self.schemas: list[dict] = []
        self._gate: threading.Event | None = None

    def queue(self, *replies: dict | str | LLMError) -> None:
        self._queue.extend(replies)

    def gate(self) -> threading.Event:
        """Hold every call until the returned event is set."""
        self._gate = threading.Event()
        return self._gate

    def chat_json(self, messages: list[ChatMessage], schema: dict) -> str:
        self.calls.append(messages)
        self.schemas.append(schema)
        if self._gate is not None:
            self._gate.wait(timeout=5)
        reply = self._queue.pop(0) if self._queue else self.default
        if isinstance(reply, LLMError):
            raise reply
        return reply if isinstance(reply, str) else json.dumps(reply, ensure_ascii=False)

    @property
    def prompts(self) -> list[str]:
        return [call[-1].content for call in self.calls]

    @property
    def last_prompt(self) -> str:
        return self.prompts[-1]
