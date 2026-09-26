"""Conversation sessions: producing the next reply of a roleplay or helper conversation.

This package is the public interface. Routers import from here, never from its modules.
"""

from app.services.conversation.engine import ConversationEngine
from app.services.conversation.pool import ConversationSessionPool
from app.services.conversation.reaper import SESSION_REAPER_INTERVAL_SECONDS, run_session_reaper
from app.services.conversation.session import (
    ConversationSession,
    SavedTurn,
    SessionCapableProvider,
    SessionFingerprint,
    SessionKey,
    SessionKind,
    TurnRequest,
)

__all__ = [
    "SESSION_REAPER_INTERVAL_SECONDS",
    "ConversationEngine",
    "ConversationSession",
    "ConversationSessionPool",
    "SavedTurn",
    "SessionCapableProvider",
    "SessionFingerprint",
    "SessionKey",
    "SessionKind",
    "TurnRequest",
    "run_session_reaper",
]
