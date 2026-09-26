"""Serve chat routes from a fresh engine per test, so tests share no session state."""

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI

from app.services.conversation import ConversationEngine, SessionCapableProvider
from app.services.conversation.pool import ConversationSessionPool
from app.services.factory import get_conversation_engine, get_session_provider
from app.services.llm.base import LLMProvider
from tests.support.stateless_session_provider import StatelessSessionProvider

TEST_MAX_LIVE = 3
TEST_IDLE_TTL = timedelta(minutes=30)


def fresh_engine() -> ConversationEngine:
    return ConversationEngine(
        ConversationSessionPool(TEST_MAX_LIVE, TEST_IDLE_TTL, clock=lambda: datetime.now(UTC))
    )


def install_session_provider(app: FastAPI, provider: SessionCapableProvider) -> ConversationEngine:
    """Serve `provider` to the chat routes through a new engine, and return that engine."""
    engine = fresh_engine()
    app.dependency_overrides[get_session_provider] = lambda: provider
    app.dependency_overrides[get_conversation_engine] = lambda: engine
    return engine


def override_conversation_engine(app: FastAPI, llm: LLMProvider) -> ConversationEngine:
    """Serve a stub LLM to the chat routes exactly as the pre-004 routers called it."""
    return install_session_provider(app, StatelessSessionProvider(llm))


def install_session_engine_only(app: FastAPI) -> ConversationEngine:
    """A fresh engine, with the session provider still built from the saved settings."""
    engine = fresh_engine()
    app.dependency_overrides[get_conversation_engine] = lambda: engine
    return engine
