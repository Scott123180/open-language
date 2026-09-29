"""SQLitePodcastStorage: an episode is a conversation plus the rows of data-model §2."""

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageRole
from app.podcasts.catalog import PODCAST_SCENARIO_ID
from app.podcasts.models import PodcastEpisode, PodcastHost, PodcastHostLine, PodcastPreferences
from app.podcasts.services.storage import (
    EpisodeRecord,
    HostLineFacts,
    HostRecord,
    LineRecord,
    NewEpisode,
    NewHost,
    NewHostLine,
    PodcastStorage,
    PreferencesRecord,
)

PREFERENCES_ID = 1


class SQLitePodcastStorage(PodcastStorage):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_episode(self, episode: NewEpisode) -> EpisodeRecord:
        conversation = _new_conversation(episode)
        try:
            self._db.add(conversation)
            self._db.flush()
            self._db.add(_new_episode_row(conversation.id, episode))
            self._db.flush()
            self._db.add_all(_new_host_row(conversation.id, host) for host in episode.hosts)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return self.get_episode(conversation.id)

    def get_episode(self, conversation_id: int) -> EpisodeRecord | None:
        row = (
            self._db.query(PodcastEpisode, Conversation)
            .join(Conversation, Conversation.id == PodcastEpisode.conversation_id)
            .filter(PodcastEpisode.conversation_id == conversation_id)
            .first()
        )
        return _episode_record(*row) if row else None

    def list_episodes(self) -> list[EpisodeRecord]:
        rows = (
            self._db.query(PodcastEpisode, Conversation)
            .join(Conversation, Conversation.id == PodcastEpisode.conversation_id)
            .order_by(Conversation.started_at.desc(), Conversation.id.desc())
            .all()
        )
        return [_episode_record(*row) for row in rows]

    def get_hosts(self, conversation_id: int) -> tuple[HostRecord, ...]:
        rows = (
            self._db.query(PodcastHost)
            .filter(PodcastHost.conversation_id == conversation_id)
            .order_by(PodcastHost.id)
            .all()
        )
        return tuple(_host_record(row) for row in rows)

    def save_host_line(self, line: NewHostLine) -> LineRecord:
        message = Message(
            conversation_id=line.conversation_id,
            role=MessageRole.ASSISTANT,
            content=line.content,
            created_at=datetime.now(UTC),
        )
        self._db.add(message)
        self._db.flush()
        facts = _new_line_row(message.id, line)
        self._db.add(facts)
        self._db.commit()
        return _line_record(message, facts)

    def get_lines(self, conversation_id: int) -> tuple[LineRecord, ...]:
        rows = (
            self._db.query(Message, PodcastHostLine)
            .outerjoin(PodcastHostLine, PodcastHostLine.message_id == Message.id)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at, Message.id)
            .all()
        )
        return tuple(_line_record(message, facts) for message, facts in rows)

    def mark_passed(self, message_id: int) -> None:
        row = self._db.get(PodcastHostLine, message_id)
        if row is not None:
            row.is_passed = True
            self._db.commit()

    def mark_revealed(self, conversation_id: int, message_id: int) -> bool:
        row = self._db.get(PodcastHostLine, message_id)
        if row is None or row.conversation_id != conversation_id:
            return False
        row.is_revealed = True
        self._db.commit()
        return True

    def get_preferences(self) -> PreferencesRecord:
        return _preferences_record(self._preferences_row())

    def save_preferences(self, preferences: PreferencesRecord) -> PreferencesRecord:
        row = self._preferences_row()
        row.last_format = preferences.last_format
        row.is_show_text_on = preferences.is_show_text_on
        row.interests = json.dumps(list(preferences.interests), ensure_ascii=False)
        row.learner_name = preferences.learner_name
        self._db.commit()
        return _preferences_record(row)

    def _preferences_row(self) -> PodcastPreferences:
        row = self._db.get(PodcastPreferences, PREFERENCES_ID)
        if row is None:
            row = PodcastPreferences(id=PREFERENCES_ID)
            self._db.add(row)
            self._db.commit()
            self._db.refresh(row)
        return row


def _new_conversation(episode: NewEpisode) -> Conversation:
    return Conversation(
        scenario_id=PODCAST_SCENARIO_ID,
        scenario_title=episode.title,
        target_language=episode.target_language,
        native_language=episode.native_language,
        llm_model=episode.llm_model,
        status=ConversationStatus.ACTIVE,
        started_at=datetime.now(UTC),
    )


def _new_episode_row(conversation_id: int, episode: NewEpisode) -> PodcastEpisode:
    return PodcastEpisode(
        conversation_id=conversation_id,
        show_source=episode.show_source,
        show_id=episode.show_id,
        premise=episode.premise,
        topic=episode.topic,
        learner_role=episode.learner_role,
        format=episode.format,
        length=episode.length,
        learner_name=episode.learner_name,
        created_at=datetime.now(UTC),
    )


def _new_host_row(conversation_id: int, host: NewHost) -> PodcastHost:
    return PodcastHost(
        conversation_id=conversation_id,
        slot=host.slot,
        name=host.name,
        personality=host.personality_id,
        voice_key=host.voice_key,
        show_role=host.show_role,
        angle=host.angle,
    )


def _new_line_row(message_id: int, line: NewHostLine) -> PodcastHostLine:
    return PodcastHostLine(
        message_id=message_id,
        conversation_id=line.conversation_id,
        host_id=line.host_id,
        intent=line.intent,
        invites_learner=line.invites_learner,
        is_passed=False,
        is_revealed=False,
        was_trimmed=line.was_trimmed,
    )


def _episode_record(episode: PodcastEpisode, conversation: Conversation) -> EpisodeRecord:
    return EpisodeRecord(
        conversation_id=episode.conversation_id,
        show_source=episode.show_source,
        show_id=episode.show_id,
        title=conversation.scenario_title,
        premise=episode.premise,
        topic=episode.topic,
        learner_role=episode.learner_role,
        format=episode.format,
        length=episode.length,
        learner_name=episode.learner_name,
        target_language=conversation.target_language,
        native_language=conversation.native_language,
        status=conversation.status.value,
        created_at=episode.created_at,
    )


def _host_record(row: PodcastHost) -> HostRecord:
    return HostRecord(
        host_id=row.id,
        slot=row.slot,
        name=row.name,
        personality_id=row.personality,
        voice_key=row.voice_key,
        show_role=row.show_role,
        angle=row.angle,
    )


def _line_record(message: Message, facts: PodcastHostLine | None) -> LineRecord:
    return LineRecord(
        message_id=message.id,
        role=message.role.value,
        content=message.content,
        created_at=message.created_at,
        host=_host_line_facts(facts) if facts is not None else None,
    )


def _host_line_facts(row: PodcastHostLine) -> HostLineFacts:
    return HostLineFacts(
        host_id=row.host_id,
        intent=row.intent,
        invites_learner=row.invites_learner,
        is_passed=row.is_passed,
        is_revealed=row.is_revealed,
        was_trimmed=row.was_trimmed,
    )


def _preferences_record(row: PodcastPreferences) -> PreferencesRecord:
    return PreferencesRecord(
        last_format=row.last_format,
        is_show_text_on=row.is_show_text_on,
        interests=tuple(json.loads(row.interests)),
        learner_name=row.learner_name,
    )
