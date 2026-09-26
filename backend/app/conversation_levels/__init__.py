"""Conversation difficulty level domain module (feature 005).

The public interface of the module: the closed set of levels, the default, the catalogue served to
the UI, and the two renderers that compose a level's rules onto an existing prompt. Callers import
only from here, never from `catalog` or `rules`.
"""

from app.conversation_levels.catalog import (
    DEFAULT_CONVERSATION_LEVEL,
    LEVEL_CATALOG,
    ConversationLevel,
)
from app.conversation_levels.rules import with_learner_text_rules, with_partner_speech_rules

__all__ = [
    "ConversationLevel",
    "DEFAULT_CONVERSATION_LEVEL",
    "LEVEL_CATALOG",
    "with_learner_text_rules",
    "with_partner_speech_rules",
]
