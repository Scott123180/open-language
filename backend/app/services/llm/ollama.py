from collections.abc import Iterator

import ollama

from app.services.llm.base import ChatMessage, LLMError, LLMProvider


class OllamaLLMProvider(LLMProvider):
    def __init__(self, model: str) -> None:
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        try:
            response = ollama.chat(
                model=self._model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                stream=True,
            )
            for chunk in response:
                yield chunk["message"]["content"]
        except Exception as e:
            raise LLMError(str(e)) from e

    def chat(self, messages: list[ChatMessage]) -> str:
        try:
            response = ollama.chat(
                model=self._model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                stream=False,
            )
            return response["message"]["content"]
        except Exception as e:
            raise LLMError(str(e)) from e
