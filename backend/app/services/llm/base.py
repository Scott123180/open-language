from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass


class LLMError(Exception):
    """A language-model request failed.

    `user_message` is safe to show the learner and names a next step. `can_retry`
    tells a caller whether a fresh session could fix the failure, without the caller
    knowing which provider raised it (FR-S11).
    """

    DEFAULT_USER_MESSAGE = "The AI is not responding. Please try again."

    def __init__(
        self, detail: str, user_message: str = DEFAULT_USER_MESSAGE, can_retry: bool = True
    ) -> None:
        super().__init__(detail)
        self._user_message = user_message
        self._can_retry = can_retry

    @property
    def user_message(self) -> str:
        return self._user_message

    @property
    def can_retry(self) -> bool:
        return self._can_retry


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
