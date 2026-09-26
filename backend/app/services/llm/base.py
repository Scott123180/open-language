from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass


class LLMError(Exception):
    pass


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMProvider(ABC):
    @abstractmethod
    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        """Stream response tokens. Raises LLMError on failure."""
        ...

    @abstractmethod
    def chat(self, messages: list[ChatMessage]) -> str:
        """Blocking chat. Returns full response string. Raises LLMError on failure."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model identifier in use."""
        ...


class StructuredLLMProvider(ABC):
    """Chat with output constrained to a JSON Schema.

    Deliberately separate from LLMProvider: streaming consumers have no use for
    a JSON method, and the corrections module has no use for streaming (ISP).
    """

    @abstractmethod
    def chat_json(self, messages: list[ChatMessage], schema: dict) -> str:
        """Return raw JSON text conforming to schema. Raises LLMError on failure."""
        ...
