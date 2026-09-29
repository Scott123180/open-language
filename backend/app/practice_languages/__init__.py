"""Practice languages: the catalogue, their names in prompts, and the voice that speaks each.

Code outside this package imports only from here, never from its modules (Principle V).
It owns no tables and no router.
"""

from app.practice_languages.catalog import (
    DEFAULT_PRACTICE_LANGUAGE,
    PRACTICE_LANGUAGES,
    PracticeLanguage,
)
from app.practice_languages.hosts import guest_labels_for, host_names_for, voice_sample_line
from app.practice_languages.naming import ConversationLanguages, UnknownLanguage, language_name
from app.practice_languages.voices import voice_for, voice_unavailable_message

__all__ = [
    "PracticeLanguage",
    "PRACTICE_LANGUAGES",
    "DEFAULT_PRACTICE_LANGUAGE",
    "UnknownLanguage",
    "language_name",
    "ConversationLanguages",
    "voice_for",
    "voice_unavailable_message",
    "host_names_for",
    "guest_labels_for",
    "voice_sample_line",
]
