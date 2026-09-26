"""ConversationEngine: produce the next reply of a roleplay or helper conversation (research R-17).

Routers hand it a `TurnRequest` and relay the tokens. They never build message lists or touch a
provider's session directly, so adding a provider changes no router.
"""

from collections.abc import Iterator, Sequence

from app.services.conversation.pool import ConversationSessionPool
from app.services.conversation.session import (
    SavedTurn,
    SessionCapableProvider,
    SessionKey,
    TurnRequest,
)


class ConversationEngine:
    def __init__(self, pool: ConversationSessionPool) -> None:
        self._pool = pool

    def stream_turn(self, provider: SessionCapableProvider, request: TurnRequest) -> Iterator[str]:
        """Yield the reply. Raises LLMError with a learner-facing message on failure."""
        return self._pool.run_turn(provider, request)

    def acknowledge(self, key: SessionKey, turn_id: str) -> None:
        """Record the saved id of the reply just produced, so the next turn lines up."""
        self._pool.acknowledge(key, turn_id)

    def warm(
        self,
        provider: SessionCapableProvider,
        key: SessionKey,
        standing_prompt: str,
        history: Sequence[SavedTurn],
    ) -> None:
        """Build the conversation's session ahead of its next turn, without generating."""
        self._pool.warm(provider, key, standing_prompt, history)

    def is_live(self, key: SessionKey) -> bool:
        return self._pool.is_live(key)

    def end(self, key: SessionKey) -> None:
        self._pool.end(key)

    def evict_idle(self) -> None:
        self._pool.evict_idle()

    def close(self) -> None:
        self._pool.close_all()
