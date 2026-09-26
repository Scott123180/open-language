"""A test-only SessionCapableProvider that behaves exactly like the pre-004 routers.

Every turn rebuilds the full message list and calls `llm.chat_stream`, with guidance appended
to the system message. Existing chat tests keep asserting on the messages their stub LLM receives.
"""

from collections.abc import Iterator, Sequence

from app.services.conversation import (
    ConversationSession,
    SavedTurn,
    SessionCapableProvider,
    SessionFingerprint,
    SessionKey,
)
from app.services.llm.base import ChatMessage, LLMError, LLMProvider
from app.services.llm.selection_types import LLMSelection

_STATELESS_PROVIDER_ID = "stateless-test"


class StatelessSession(ConversationSession):
    def __init__(self, llm: LLMProvider, fingerprint, standing_prompt, history) -> None:
        self._llm = llm
        self._fingerprint = fingerprint
        self._standing_prompt = standing_prompt
        self._turns = [ChatMessage(turn.role, turn.content) for turn in history]
        self._synced = [turn.turn_id for turn in history]
        self._last_reply = ""
        self._is_closed = False

    @property
    def fingerprint(self) -> SessionFingerprint:
        return self._fingerprint

    @property
    def synced_turn_ids(self) -> Sequence[str]:
        return tuple(self._synced)

    @property
    def is_broken(self) -> bool:
        return False

    def warm(self) -> None:
        """Nothing to warm: the stub keeps nothing loaded."""

    def reply(self, pending: Sequence[SavedTurn], guidance: str | None) -> Iterator[str]:
        new_turns = [ChatMessage(turn.role, turn.content) for turn in pending]
        yield from self._generate(self._turns + new_turns, guidance)
        self._turns.extend(new_turns)
        self._synced.extend(turn.turn_id for turn in pending)

    def reply_to_opening(self, instruction: str) -> Iterator[str]:
        yield from self._generate([*self._turns, ChatMessage("user", instruction)], None)

    def acknowledge(self, turn_id: str) -> None:
        self._turns.append(ChatMessage("assistant", self._last_reply))
        self._synced.append(turn_id)

    def close(self) -> None:
        self._is_closed = True

    def _generate(self, turns: list[ChatMessage], guidance: str | None) -> Iterator[str]:
        if self._is_closed:
            raise LLMError("session closed")
        system = ChatMessage("system", self._standing_prompt + (guidance or ""))
        tokens = list(self._llm.chat_stream([system, *turns]))
        self._last_reply = "".join(tokens)
        yield from tokens


class StatelessSessionProvider(SessionCapableProvider):
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def session_fingerprint(self, standing_prompt: str) -> SessionFingerprint:
        selection = LLMSelection(_STATELESS_PROVIDER_ID, self._llm.model_name)
        return SessionFingerprint(selection, "", SessionFingerprint.digest_prompt(standing_prompt))

    def open_session(
        self, key: SessionKey, standing_prompt: str, history: Sequence[SavedTurn]
    ) -> StatelessSession:
        fingerprint = self.session_fingerprint(standing_prompt)
        return StatelessSession(self._llm, fingerprint, standing_prompt, history)
