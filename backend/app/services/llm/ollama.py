from collections.abc import Iterator, Sequence

import ollama

from app.services.conversation.session import (
    ConversationSession,
    SavedTurn,
    SessionCapableProvider,
    SessionFingerprint,
    SessionKey,
)
from app.services.llm.base import (
    ChatMessage,
    LLMError,
    LLMProvider,
    StructuredLLMProvider,
)
from app.services.llm.catalog import OLLAMA_PROVIDER_ID
from app.services.llm.ollama_residency import OllamaResidency
from app.services.llm.ollama_session import OllamaSession, OllamaSessionConfig
from app.services.llm.selection_types import LLMSelection

_NO_EFFORT = ""


class OllamaLLMProvider(LLMProvider, StructuredLLMProvider, SessionCapableProvider):
    def __init__(self, client: ollama.Client, model: str, residency: OllamaResidency) -> None:
        self._client = client
        self._model = model
        self._residency = residency

    @property
    def model_name(self) -> str:
        return self._model

    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        try:
            response = self._client.chat(
                model=self._model,
                messages=_to_wire(messages),
                stream=True,
                keep_alive=self._residency.keep_alive_for(self._model),
            )
            for chunk in response:
                yield chunk["message"]["content"]
        except Exception as e:
            raise LLMError(str(e)) from e

    def chat(self, messages: list[ChatMessage]) -> str:
        try:
            response = self._client.chat(
                model=self._model,
                messages=_to_wire(messages),
                stream=False,
                keep_alive=self._residency.keep_alive_for(self._model),
            )
            return response["message"]["content"]
        except Exception as e:
            raise LLMError(str(e)) from e

    def chat_json(self, messages: list[ChatMessage], schema: dict) -> str:
        try:
            response = self._client.chat(
                model=self._model,
                messages=_to_wire(messages),
                stream=False,
                format=schema,
                keep_alive=self._residency.keep_alive_for(self._model),
            )
            return response["message"]["content"]
        except Exception as e:
            raise LLMError(str(e)) from e

    def session_fingerprint(self, standing_prompt: str) -> SessionFingerprint:
        selection = LLMSelection(OLLAMA_PROVIDER_ID, self._model)
        digest = SessionFingerprint.digest_prompt(standing_prompt)
        return SessionFingerprint(selection, _NO_EFFORT, digest)

    def open_session(
        self, key: SessionKey, standing_prompt: str, history: Sequence[SavedTurn]
    ) -> ConversationSession:
        config = OllamaSessionConfig(
            client=self._client,
            model=self._model,
            keep_alive=self._residency.session_keep_alive,
            fingerprint=self.session_fingerprint(standing_prompt),
            standing_prompt=standing_prompt,
            residency=self._residency,
        )
        self._residency.hold(self._model)
        return OllamaSession(config, history)


def _to_wire(messages: list[ChatMessage]) -> list[dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in messages]
