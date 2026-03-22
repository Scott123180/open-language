from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.app_settings import AppSettings
from app.models.conversation import Conversation, ConversationStatus
from app.models.learning_tool_result import LearningToolResult, ToolType
from app.models.message import InputSource, Message, MessageRole
from app.models.vocabulary_item import VocabularyItem
from app.services.storage.base import (
    AppSettingsRecord,
    ConversationRecord,
    LearningToolResultRecord,
    MessageRecord,
    StorageProvider,
    VocabularyItemRecord,
)


def _conv_to_record(c: Conversation) -> ConversationRecord:
    return ConversationRecord(
        id=c.id,
        scenario_id=c.scenario_id,
        scenario_title=c.scenario_title,
        target_language=c.target_language,
        native_language=c.native_language,
        status=c.status.value,
        started_at=c.started_at,
        ended_at=c.ended_at,
        llm_model=c.llm_model,
        custom_prompt=c.custom_prompt,
    )


def _msg_to_record(m: Message) -> MessageRecord:
    return MessageRecord(
        id=m.id,
        conversation_id=m.conversation_id,
        role=m.role.value,
        content=m.content,
        input_source=m.input_source.value if m.input_source else None,
        created_at=m.created_at,
        tts_audio_path=m.tts_audio_path,
    )


def _tool_to_record(r: LearningToolResult) -> LearningToolResultRecord:
    return LearningToolResultRecord(
        id=r.id,
        message_id=r.message_id,
        tool_type=r.tool_type.value,
        input_selection=r.input_selection,
        result=r.result,
        created_at=r.created_at,
    )


def _vocab_to_record(v: VocabularyItem) -> VocabularyItemRecord:
    return VocabularyItemRecord(
        id=v.id,
        word=v.word,
        translation=v.translation,
        target_language=v.target_language,
        native_language=v.native_language,
        source_conversation_id=v.source_conversation_id,
        saved_at=v.saved_at,
    )


def _settings_to_record(s: AppSettings) -> AppSettingsRecord:
    return AppSettingsRecord(
        llm_model=s.llm_model,
        target_language=s.target_language,
        native_language=s.native_language,
        tts_voice=s.tts_voice,
        suggestion_count=s.suggestion_count,
        whisper_model=s.whisper_model,
        updated_at=s.updated_at,
    )


class SQLiteStorageProvider(StorageProvider):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_conversation(
        self,
        scenario_id: str,
        scenario_title: str,
        target_language: str,
        native_language: str,
        llm_model: str,
        custom_prompt: str | None = None,
    ) -> ConversationRecord:
        conv = Conversation(
            scenario_id=scenario_id,
            scenario_title=scenario_title,
            target_language=target_language,
            native_language=native_language,
            llm_model=llm_model,
            status=ConversationStatus.ACTIVE,
            started_at=datetime.now(UTC),
            custom_prompt=custom_prompt,
        )
        self._db.add(conv)
        self._db.commit()
        self._db.refresh(conv)
        return _conv_to_record(conv)

    def complete_conversation(self, conversation_id: int) -> ConversationRecord:
        conv = self._db.get(Conversation, conversation_id)
        conv.status = ConversationStatus.COMPLETED
        conv.ended_at = datetime.now(UTC)
        self._db.commit()
        self._db.refresh(conv)
        return _conv_to_record(conv)

    def get_conversation(self, conversation_id: int) -> ConversationRecord | None:
        conv = self._db.get(Conversation, conversation_id)
        return _conv_to_record(conv) if conv else None

    def list_conversations(self) -> list[ConversationRecord]:
        rows = self._db.query(Conversation).order_by(Conversation.started_at.desc()).all()
        return [_conv_to_record(r) for r in rows]

    def save_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        input_source: str | None = None,
    ) -> MessageRecord:
        msg = Message(
            conversation_id=conversation_id,
            role=MessageRole(role),
            content=content,
            input_source=InputSource(input_source) if input_source else None,
            created_at=datetime.now(UTC),
        )
        self._db.add(msg)
        self._db.commit()
        self._db.refresh(msg)
        return _msg_to_record(msg)

    def get_messages(self, conversation_id: int) -> list[MessageRecord]:
        rows = (
            self._db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        return [_msg_to_record(r) for r in rows]

    def get_message(self, message_id: int) -> MessageRecord | None:
        msg = self._db.get(Message, message_id)
        return _msg_to_record(msg) if msg else None

    def set_tts_path(self, message_id: int, audio_path: str) -> MessageRecord:
        msg = self._db.get(Message, message_id)
        msg.tts_audio_path = audio_path
        self._db.commit()
        self._db.refresh(msg)
        return _msg_to_record(msg)

    def get_or_create_learning_result(
        self,
        message_id: int,
        tool_type: str,
        input_selection: str | None,
        compute: Callable[[], str],
    ) -> LearningToolResultRecord:
        existing = (
            self._db.query(LearningToolResult)
            .filter(
                LearningToolResult.message_id == message_id,
                LearningToolResult.tool_type == ToolType(tool_type),
                LearningToolResult.input_selection == input_selection,
            )
            .first()
        )
        if existing:
            return _tool_to_record(existing)
        result_text = compute()
        row = LearningToolResult(
            message_id=message_id,
            tool_type=ToolType(tool_type),
            input_selection=input_selection,
            result=result_text,
            created_at=datetime.now(UTC),
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return _tool_to_record(row)

    def save_vocabulary_item(
        self,
        word: str,
        translation: str,
        target_language: str,
        native_language: str,
        source_conversation_id: int | None = None,
    ) -> VocabularyItemRecord:
        existing = (
            self._db.query(VocabularyItem)
            .filter(
                VocabularyItem.word == word,
                VocabularyItem.target_language == target_language,
            )
            .first()
        )
        if existing:
            return _vocab_to_record(existing)
        item = VocabularyItem(
            word=word,
            translation=translation,
            target_language=target_language,
            native_language=native_language,
            source_conversation_id=source_conversation_id,
            saved_at=datetime.now(UTC),
        )
        self._db.add(item)
        self._db.commit()
        self._db.refresh(item)
        return _vocab_to_record(item)

    def list_vocabulary(self) -> list[VocabularyItemRecord]:
        rows = self._db.query(VocabularyItem).order_by(VocabularyItem.saved_at.desc()).all()
        return [_vocab_to_record(r) for r in rows]

    def get_settings(self) -> AppSettingsRecord:
        settings = self._db.get(AppSettings, 1)
        if settings is None:
            settings = AppSettings(
                id=1,
                updated_at=datetime.now(UTC),
            )
            self._db.add(settings)
            self._db.commit()
            self._db.refresh(settings)
        return _settings_to_record(settings)

    def update_settings(self, **kwargs) -> AppSettingsRecord:
        settings = self._db.get(AppSettings, 1)
        if settings is None:
            settings = AppSettings(id=1, updated_at=datetime.now(UTC))
            self._db.add(settings)
        for key, value in kwargs.items():
            setattr(settings, key, value)
        settings.updated_at = datetime.now(UTC)
        self._db.commit()
        self._db.refresh(settings)
        return _settings_to_record(settings)
