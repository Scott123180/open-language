"""An Ollama conversation session: the turns in memory, and the model kept loaded (research R-13).

Ollama's chat API is stateless, so each turn still sends the whole list. What the session buys
is `keep_alive`: the model stays loaded between turns instead of unloading after five minutes,
until the model's last session closes (see `ollama_residency`).
"""

import logging
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

import ollama

from app.services.conversation.session import (
    ConversationSession,
    SavedTurn,
    SessionFingerprint,
)
from app.services.llm.base import LLMError
from app.services.llm.ollama_residency import OllamaResidency

logger = logging.getLogger(__name__)

_SYSTEM_ROLE = "system"
_USER_ROLE = "user"
_ASSISTANT_ROLE = "assistant"
_EMPTY_PRELOAD_PROMPT = ""
_CLOSED_DETAIL = "This Ollama session was closed"


@dataclass(frozen=True)
class OllamaSessionConfig:
    client: ollama.Client
    model: str
    keep_alive: str
    fingerprint: SessionFingerprint
    standing_prompt: str
    residency: OllamaResidency


class OllamaSession(ConversationSession):
    def __init__(self, config: OllamaSessionConfig, history: Sequence[SavedTurn]) -> None:
        self._config = config
        self._turns = [_wire(turn.role, turn.content) for turn in history]
        self._synced = [turn.turn_id for turn in history]
        self._last_reply = ""
        self._is_broken = False
        self._is_closed = False

    @property
    def fingerprint(self) -> SessionFingerprint:
        return self._config.fingerprint

    @property
    def synced_turn_ids(self) -> Sequence[str]:
        return tuple(self._synced)

    @property
    def is_broken(self) -> bool:
        return self._is_broken

    def warm(self) -> None:
        self._require_open()
        try:
            self._config.client.generate(
                model=self._config.model,
                prompt=_EMPTY_PRELOAD_PROMPT,
                keep_alive=self._config.keep_alive,
            )
        except Exception as exc:
            raise self._broken(exc) from exc

    def reply(self, pending: Sequence[SavedTurn], guidance: str | None) -> Iterator[str]:
        new_turns = [_wire(turn.role, turn.content) for turn in pending]
        yield from self._generate([*self._turns, *new_turns], guidance)
        self._turns.extend(new_turns)
        self._synced.extend(turn.turn_id for turn in pending)

    def reply_to_opening(self, instruction: str) -> Iterator[str]:
        yield from self._generate([*self._turns, _wire(_USER_ROLE, instruction)], None)

    def acknowledge(self, turn_id: str) -> None:
        self._turns.append(_wire(_ASSISTANT_ROLE, self._last_reply))
        self._synced.append(turn_id)

    def close(self) -> None:
        if self._is_closed:
            return
        self._is_closed = True
        if self._config.residency.release(self._config.model):
            self._hand_model_back()

    def _hand_model_back(self) -> None:
        """Return the model to Ollama's own keep-alive now that no session holds it (FR-S06).

        Ollama can only change a model's timer through a request, so this is an empty preload
        with `keep_alive` unset: it costs nothing while the model is loaded.
        """
        try:
            self._config.client.generate(model=self._config.model, prompt=_EMPTY_PRELOAD_PROMPT)
        except Exception as exc:  # noqa: BLE001 — close must succeed; the model then idles out
            logger.warning(
                "Could not return %s to Ollama's keep-alive: %s", self._config.model, exc
            )

    def _generate(self, turns: list[dict[str, str]], guidance: str | None) -> Iterator[str]:
        self._require_open()
        system = _wire(_SYSTEM_ROLE, self._config.standing_prompt + (guidance or ""))
        parts: list[str] = []
        try:
            for chunk in self._stream([system, *turns]):
                parts.append(chunk)
                yield chunk
        except Exception as exc:
            raise self._broken(exc) from exc
        self._last_reply = "".join(parts)

    def _stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        response = self._config.client.chat(
            model=self._config.model,
            messages=messages,
            stream=True,
            keep_alive=self._config.keep_alive,
        )
        for chunk in response:
            yield chunk["message"]["content"]

    def _require_open(self) -> None:
        if self._is_closed:
            raise LLMError(_CLOSED_DETAIL)

    def _broken(self, exc: Exception) -> LLMError:
        self._is_broken = True
        return LLMError(str(exc))


def _wire(role: str, content: str) -> dict[str, str]:
    return {"role": role, "content": content}
