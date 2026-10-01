"""Running one engine turn and relaying it to the client as server-sent events."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from functools import partial

from app.services.conversation import (
    ConversationEngine,
    SavedTurn,
    SessionCapableProvider,
    SessionKey,
    TurnRequest,
)
from app.services.llm.base import LLMError

logger = logging.getLogger(__name__)


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@dataclass(frozen=True)
class SavedReply:
    """Where a finished reply was stored, and the frame that tells the client."""

    turn_id: str
    done_frame: dict


@dataclass(frozen=True)
class EngineTurn:
    engine: ConversationEngine
    provider: SessionCapableProvider
    request: TurnRequest

    def collect(self) -> list[str]:
        # Delivery stays batched (spec Assumptions): the whole reply is collected first.
        return list(self.engine.stream_turn(self.provider, self.request))


async def relay_engine_reply(
    turn: EngineTurn, persist: Callable[[str], SavedReply]
) -> AsyncIterator[str]:
    """Run the turn, relay its tokens, store the reply, and tell the session its saved id."""
    loop = asyncio.get_running_loop()
    try:
        tokens = await loop.run_in_executor(None, turn.collect)
    except LLMError as exc:
        yield sse({"error": exc.user_message})
        return
    for token in tokens:
        yield sse({"token": token})
    saved = persist("".join(tokens))
    await loop.run_in_executor(None, turn.engine.acknowledge, turn.request.key, saved.turn_id)
    yield sse(saved.done_frame)


def start_warming(
    engine: ConversationEngine,
    provider: SessionCapableProvider,
    key: SessionKey,
    standing_prompt: str,
    history: tuple[SavedTurn, ...],
) -> None:
    warm = partial(engine.warm, provider, key, standing_prompt, history)
    asyncio.get_running_loop().run_in_executor(None, _warm_quietly, warm)


def _warm_quietly(warm: Callable[[], None]) -> None:
    """A failed warm-up is never shown: the first real turn reports the problem."""
    try:
        warm()
    except LLMError as exc:
        logger.warning("Session warm-up failed; the next turn will try again: %s", exc)
