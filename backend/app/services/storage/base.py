from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime

from app.conversation_levels import DEFAULT_CONVERSATION_LEVEL
from app.services.llm.catalog import DEFAULT_PROVIDER_ID
from app.services.llm.selection_types import DEFAULT_EFFORT

DEFAULT_SUMMARY_LANGUAGE = "conversation"
"""A summary opens in the conversation's own language until the learner picks English."""


@dataclass(frozen=True)
class ConversationRecord:
    id: int
    scenario_id: str
    scenario_title: str
    target_language: str
    native_language: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    llm_model: str
    custom_prompt: str | None = None


@dataclass(frozen=True)
class MessageRecord:
    id: int
    conversation_id: int
    role: str
    content: str
    input_source: str | None
    created_at: datetime
    tts_audio_path: str | None
    transcription_confidence: float | None = None
    is_low_confidence: bool | None = None


@dataclass(frozen=True)
class LearningToolResultRecord:
    id: int
    message_id: int
    tool_type: str
    input_selection: str | None
    result: str
    created_at: datetime


@dataclass(frozen=True)
class VocabularyItemRecord:
    id: int
    word: str
    translation: str
    target_language: str
    native_language: str
    source_conversation_id: int | None
    saved_at: datetime
    already_saved: bool = False


@dataclass(frozen=True)
class AppSettingsRecord:
    llm_model: str
    target_language: str
    native_language: str
    suggestion_count: int
    whisper_model: str
    updated_at: datetime
    correction_mode: str = "off"
    llm_provider: str = DEFAULT_PROVIDER_ID
    llm_effort: str = DEFAULT_EFFORT
    conversation_level: str = DEFAULT_CONVERSATION_LEVEL.value
    summary_language: str = DEFAULT_SUMMARY_LANGUAGE
    voice_choices: Mapping[str, str] = field(default_factory=dict)
    """The learner's explicit voice per practice-language code. No entry means the default."""


class StorageProvider(ABC):
    @abstractmethod
    def create_conversation(
        self,
        scenario_id: str,
        scenario_title: str,
        target_language: str,
        native_language: str,
        llm_model: str,
        custom_prompt: str | None = None,
    ) -> ConversationRecord:
        """Create and return a new active conversation."""
        ...

    @abstractmethod
    def complete_conversation(self, conversation_id: int) -> ConversationRecord:
        """Mark conversation as completed, set ended_at to now."""
        ...

    @abstractmethod
    def get_conversation(self, conversation_id: int) -> ConversationRecord | None:
        """Return conversation by id, or None if not found."""
        ...

    @abstractmethod
    def list_conversations(self) -> list[ConversationRecord]:
        """Return all conversations, most recent first."""
        ...

    @abstractmethod
    def save_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        input_source: str | None = None,
        transcription_confidence: float | None = None,
        is_low_confidence: bool | None = None,
    ) -> MessageRecord:
        """Persist a message and return the saved record."""
        ...

    @abstractmethod
    def get_messages(self, conversation_id: int) -> list[MessageRecord]:
        """Return all messages for a conversation ordered by created_at asc."""
        ...

    @abstractmethod
    def get_message(self, message_id: int) -> MessageRecord | None:
        """Return a single message by id, or None if not found."""
        ...

    @abstractmethod
    def set_tts_path(self, message_id: int, audio_path: str) -> MessageRecord:
        """Update tts_audio_path on a message record."""
        ...

    @abstractmethod
    def get_or_create_learning_result(
        self,
        message_id: int,
        tool_type: str,
        input_selection: str | None,
        compute: Callable[[], str],
    ) -> LearningToolResultRecord:
        """Return cached result if exists, otherwise call compute() and persist."""
        ...

    @abstractmethod
    def save_vocabulary_item(
        self,
        word: str,
        translation: str,
        target_language: str,
        native_language: str,
        source_conversation_id: int | None = None,
    ) -> VocabularyItemRecord:
        """Insert word if not exists (idempotent by word+target_language), return record."""
        ...

    @abstractmethod
    def list_vocabulary(self) -> list[VocabularyItemRecord]:
        """Return all vocabulary items, most recently saved first."""
        ...

    @abstractmethod
    def get_settings(self) -> AppSettingsRecord:
        """Return app settings, creating defaults if not yet persisted."""
        ...

    @abstractmethod
    def update_settings(self, **kwargs) -> AppSettingsRecord:
        """Update specified fields and return updated record."""
        ...

    @abstractmethod
    def save_voice_choice(self, target_language: str, voice_key: str) -> None:
        """Remember the learner's voice for one language (upsert)."""
        ...
