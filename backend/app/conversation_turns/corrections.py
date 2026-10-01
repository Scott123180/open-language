"""Planning corrections for a learner's turn, and the feedback frame that reports them."""

import asyncio
import json
import logging
from dataclasses import dataclass

from app.config import get_settings
from app.corrections.schemas import rendered_notes, to_note_payload
from app.corrections.services.storage import CorrectionStorageProvider
from app.corrections.services.strategies import (
    NULL_TURN_PLAN,
    CorrectionStrategy,
    TurnContext,
    TurnPlan,
)
from app.practice_languages import ConversationLanguages
from app.services.llm.base import LLMError
from app.services.storage.base import ConversationRecord, MessageRecord

logger = logging.getLogger(__name__)


def _languages_of(conversation: ConversationRecord) -> ConversationLanguages:
    """Prompts name the conversation's languages ("German"), never their codes (research R2)."""
    return ConversationLanguages.of(conversation.target_language, conversation.native_language)


async def _plan_turn_failing_open(
    strategy: CorrectionStrategy, context: TurnContext, timeout: float
) -> TurnPlan:
    """FR-026: every evaluation failure ends the same way — an empty plan."""
    try:
        return await asyncio.wait_for(strategy.plan_turn(context), timeout=timeout)
    except (TimeoutError, LLMError) as exc:
        logger.warning("Correction evaluation failed (%r); continuing uncorrected", exc)
        return NULL_TURN_PLAN


def _persist_feedback(
    correction_storage: CorrectionStorageProvider, message_id: int, plan: TurnPlan
) -> list:
    """Store the turn's notes and return only those a client renders."""
    if not plan.feedback:
        return []
    return rendered_notes(correction_storage.save_feedback(message_id, plan.feedback))


def _feedback_frame(message_id: int, notes: list, awaiting_retry: bool) -> str:
    payload = {
        "event": "feedback",
        "message_id": message_id,
        "awaiting_retry": awaiting_retry,
        "notes": [to_note_payload(note) for note in notes],
    }
    return f"data: {json.dumps(payload)}\n\n"


def _last_character_line(history: list) -> str | None:
    return next((m.content for m in reversed(history) if m.role == "assistant"), None)


def _turn_context(
    conversation,
    conversation_id: int,
    content: str,
    history: list,
    is_low_confidence: bool = False,
) -> TurnContext:
    languages = _languages_of(conversation)
    return TurnContext(
        conversation_id=conversation_id,
        learner_text=content,
        target_language=languages.target_name,
        native_language=languages.native_name,
        preceding_character_line=_last_character_line(history),
        is_low_confidence=is_low_confidence,
    )


@dataclass(frozen=True)
class Corrections:
    strategy: CorrectionStrategy
    storage: CorrectionStorageProvider

    def feedback_frame(self, conversation_id: int, message_id: int, plan: TurnPlan) -> str | None:
        notes = _persist_feedback(self.storage, message_id, plan)
        if not notes:
            return None
        awaiting_retry = self.storage.get_pause_state(conversation_id).awaiting_retry
        return _feedback_frame(message_id, notes, awaiting_retry)


async def plan_learner_turn(
    corrections: Corrections,
    conversation: ConversationRecord,
    learner_message: MessageRecord,
    preceding: list[MessageRecord],
) -> TurnPlan:
    is_low_confidence = bool(learner_message.is_low_confidence)
    context = _turn_context(
        conversation, conversation.id, learner_message.content, preceding, is_low_confidence
    )
    timeout = get_settings().correction_timeout_seconds
    return await _plan_turn_failing_open(corrections.strategy, context, timeout)
