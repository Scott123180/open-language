"""The SQLite show library and series storage (010 data-model §2.1–§2.5, §4).

A ready-made show's row holds only its template id: its content is always read from the
catalogue. Every row keeps the lifetime rules of data-model §2.1, and every memory write is
pruned to the caps and the text budget in the transaction that wrote it.
"""

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message
from app.podcasts.catalog import (
    LEAD_SLOT,
    LEARNER_POINT,
    MAX_REMEMBERED_ABOUT_LEARNER,
    MAX_REMEMBERED_TOPICS,
    MIN_LINES_TO_REMEMBER,
    REMEMBERED_TEXT_BUDGET,
    TOPIC_POINT,
)
from app.podcasts.models import (
    PodcastSeries,
    PodcastSeriesEpisode,
    PodcastSeriesHost,
    PodcastSeriesMemory,
    PodcastShow,
)
from app.podcasts.services.series_storage import (
    EpisodeRef,
    KeptShow,
    MemoryReply,
    PendingEpisode,
    PointText,
    RememberedPoint,
    SeriesAlreadyExists,
    SeriesHost,
    SeriesRecord,
    SeriesStorage,
    ShelfEntry,
    ShowContent,
    ShowLibraryStorage,
    ShowRef,
)

Clock = Callable[[], datetime]
_NEVER = datetime.min


def _now() -> datetime:
    return datetime.now(UTC)


class SQLiteShowLibraryStorage(ShowLibraryStorage):
    def __init__(self, db: Session, clock: Clock = _now) -> None:
        self._db = db
        self._clock = clock

    def keep(self, content: ShowContent) -> KeptShow:
        row = self._find(content)
        if row is None:
            row = _new_show_row(content, self._clock())
            self._db.add(row)
            self._db.commit()
        return _kept_show(row)

    def get(self, ref: ShowRef) -> KeptShow | None:
        query = self._db.query(PodcastShow)
        if ref.template_id is not None:
            row = query.filter(PodcastShow.template_id == ref.template_id).first()
        else:
            row = query.filter(
                PodcastShow.id == ref.saved_show_id, PodcastShow.template_id.is_(None)
            ).first()
        return _kept_show(row) if row is not None else None

    def find(self, content: ShowContent) -> KeptShow | None:
        row = self._find(content)
        return _kept_show(row) if row is not None else None

    def set_favourite(self, show_row_id: int, is_favourite: bool) -> KeptShow | None:
        row = self._db.get(PodcastShow, show_row_id)
        if row is None:
            return None
        row.favourited_at = self._clock() if is_favourite else None
        is_deleted = _drop_if_unkept(self._db, row)
        self._db.commit()
        return None if is_deleted else _kept_show(row)

    def touch_played(self, show_row_id: int) -> None:
        row = self._db.get(PodcastShow, show_row_id)
        if row is not None:
            row.last_played_at = self._clock()
            self._db.commit()

    def list_mine(self, language: str) -> list[ShelfEntry]:
        rows = self._mine_rows(language)
        ordered = sorted(rows, key=lambda pair: _latest_activity(pair[0]), reverse=True)
        return [
            ShelfEntry(_kept_show(show), _series_record(self._db, series) if series else None)
            for show, series in ordered
        ]

    def forget(self, saved_show_id: int) -> bool:
        deleted = (
            self._db.query(PodcastShow)
            .filter(PodcastShow.id == saved_show_id, PodcastShow.template_id.is_(None))
            .delete()
        )
        self._db.commit()
        return deleted > 0

    def _find(self, content: ShowContent) -> PodcastShow | None:
        query = self._db.query(PodcastShow)
        if content.is_ready_made:
            return query.filter(PodcastShow.template_id == content.template_id).first()
        lead, second = content.personalities
        lead_angle, second_angle = content.angles
        return query.filter_by(
            template_id=None,
            title=content.title,
            premise=content.premise,
            topic=content.topic,
            learner_role=content.learner_role,
            lead_personality=lead,
            second_personality=second,
            lead_angle=lead_angle,
            second_angle=second_angle,
        ).first()

    def _mine_rows(self, language: str) -> list[tuple[PodcastShow, PodcastSeries | None]]:
        in_language = and_(
            PodcastSeries.show_id == PodcastShow.id, PodcastSeries.target_language == language
        )
        played_learner_made = and_(
            PodcastShow.template_id.is_(None), PodcastShow.last_played_at.is_not(None)
        )
        return (
            self._db.query(PodcastShow, PodcastSeries)
            .outerjoin(PodcastSeries, in_language)
            .filter(
                or_(
                    PodcastShow.favourited_at.is_not(None),
                    PodcastSeries.id.is_not(None),
                    played_learner_made,
                )
            )
            .all()
        )


class SQLiteSeriesStorage(SeriesStorage):
    def __init__(self, db: Session, clock: Clock = _now) -> None:
        self._db = db
        self._clock = clock

    def find(self, show_row_id: int, language: str) -> SeriesRecord | None:
        row = (
            self._db.query(PodcastSeries)
            .filter(PodcastSeries.show_id == show_row_id, PodcastSeries.target_language == language)
            .first()
        )
        return _series_record(self._db, row) if row is not None else None

    def get(self, series_id: int) -> SeriesRecord | None:
        row = self._db.get(PodcastSeries, series_id)
        return _series_record(self._db, row) if row is not None else None

    def create(
        self, show_row_id: int, language: str, hosts: tuple[SeriesHost, SeriesHost]
    ) -> SeriesRecord:
        row = PodcastSeries(show_id=show_row_id, target_language=language, created_at=self._clock())
        try:
            self._db.add(row)
            self._db.flush()
            self._db.add_all(_new_series_host_row(row.id, host, 0) for host in hosts)
            self._db.commit()
        except IntegrityError as clash:
            self._db.rollback()
            raise SeriesAlreadyExists(f"show {show_row_id} has a {language} series") from clash
        return _series_record(self._db, row)

    def recast(self, series_id: int, host: SeriesHost) -> SeriesRecord:
        row = (
            self._db.query(PodcastSeriesHost)
            .filter(PodcastSeriesHost.series_id == series_id, PodcastSeriesHost.slot == host.slot)
            .one()
        )
        _copy_host(host, row)
        row.joined_after_episodes = _episode_count(self._db, series_id)
        self._db.commit()
        return self.get(series_id)

    def reset(self, series_id: int) -> bool:
        row = self._db.get(PodcastSeries, series_id)
        if row is None:
            return False
        show = self._db.get(PodcastShow, row.show_id)
        self._db.query(PodcastSeries).filter(PodcastSeries.id == series_id).delete()
        self._db.expire(show)
        _drop_if_unkept(self._db, show)
        self._db.commit()
        return True

    def remembered(self, series_id: int) -> tuple[RememberedPoint, ...]:
        rows = (
            self._db.query(PodcastSeriesMemory, PodcastSeriesEpisode.episode_number)
            .join(
                PodcastSeriesEpisode,
                PodcastSeriesEpisode.conversation_id == PodcastSeriesMemory.conversation_id,
            )
            .filter(PodcastSeriesMemory.series_id == series_id)
            .order_by(PodcastSeriesMemory.created_at.desc(), PodcastSeriesMemory.id.desc())
            .all()
        )
        return tuple(_remembered_point(memory, number) for memory, number in rows)

    def pending_episodes(self, series_id: int) -> tuple[PendingEpisode, ...]:
        links = (
            self._db.query(PodcastSeriesEpisode)
            .filter(PodcastSeriesEpisode.series_id == series_id)
            .order_by(PodcastSeriesEpisode.episode_number, PodcastSeriesEpisode.conversation_id)
            .all()
        )
        return tuple(
            PendingEpisode(
                link.conversation_id, link.episode_number, link.remembered_up_to_message_id
            )
            for link in links
            if self._unread_count(link) >= MIN_LINES_TO_REMEMBER
        )

    def remember(
        self,
        series_id: int,
        conversation_id: int,
        reply: MemoryReply,
        up_to_message_id: int | None,
    ) -> None:
        try:
            self._write_points(series_id, conversation_id, reply)
            self._prune(series_id)
            self._move_marker(conversation_id, up_to_message_id)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def _unread_count(self, link: PodcastSeriesEpisode) -> int:
        query = self._db.query(func.count(Message.id)).filter(
            Message.conversation_id == link.conversation_id
        )
        if link.remembered_up_to_message_id is not None:
            query = query.filter(Message.id > link.remembered_up_to_message_id)
        return query.scalar()

    def _write_points(self, series_id: int, conversation_id: int, reply: MemoryReply) -> None:
        if reply.topic is not None:
            self._db.query(PodcastSeriesMemory).filter(
                PodcastSeriesMemory.series_id == series_id,
                PodcastSeriesMemory.conversation_id == conversation_id,
                PodcastSeriesMemory.kind == TOPIC_POINT,
            ).delete()
            self._add_point(series_id, conversation_id, TOPIC_POINT, reply.topic)
        for text in reply.about_learner:
            self._add_point(series_id, conversation_id, LEARNER_POINT, text)
        self._db.flush()

    def _add_point(self, series_id: int, conversation_id: int, kind: str, text: PointText) -> None:
        self._db.add(
            PodcastSeriesMemory(
                series_id=series_id,
                conversation_id=conversation_id,
                kind=kind,
                conversation_language=text.conversation_language,
                english=text.english,
                created_at=self._clock(),
            )
        )

    def _prune(self, series_id: int) -> None:
        """Newest wins: first within each kind's cap, then within the text budget (R7)."""
        self._cap(series_id, TOPIC_POINT, MAX_REMEMBERED_TOPICS)
        self._cap(series_id, LEARNER_POINT, MAX_REMEMBERED_ABOUT_LEARNER)
        self._fit_budget(series_id)

    def _cap(self, series_id: int, kind: str, cap: int) -> None:
        stale = [
            memory_id
            for (memory_id,) in self._newest_first(series_id)
            .filter(PodcastSeriesMemory.kind == kind)
            .offset(cap)
            .all()
        ]
        if stale:
            self._db.query(PodcastSeriesMemory).filter(PodcastSeriesMemory.id.in_(stale)).delete()

    def _newest_first(self, series_id: int):
        return (
            self._db.query(PodcastSeriesMemory.id)
            .filter(PodcastSeriesMemory.series_id == series_id)
            .order_by(PodcastSeriesMemory.created_at.desc(), PodcastSeriesMemory.id.desc())
        )

    def _fit_budget(self, series_id: int) -> None:
        oldest_first = (
            self._db.query(PodcastSeriesMemory)
            .filter(PodcastSeriesMemory.series_id == series_id)
            .order_by(PodcastSeriesMemory.created_at, PodcastSeriesMemory.id)
            .all()
        )
        total = sum(len(memory.conversation_language) for memory in oldest_first)
        for memory in oldest_first:
            if total <= REMEMBERED_TEXT_BUDGET:
                return
            total -= len(memory.conversation_language)
            self._db.delete(memory)

    def _move_marker(self, conversation_id: int, up_to_message_id: int | None) -> None:
        if up_to_message_id is not None:
            link = self._db.get(PodcastSeriesEpisode, conversation_id)
            link.remembered_up_to_message_id = up_to_message_id


# --- rows and records ---------------------------------------------------------------------


def _new_show_row(content: ShowContent, now: datetime) -> PodcastShow:
    if content.is_ready_made:
        return PodcastShow(template_id=content.template_id, source=content.source, created_at=now)
    return PodcastShow(
        template_id=None,
        source=content.source,
        title=content.title,
        premise=content.premise,
        topic=content.topic,
        learner_role=content.learner_role,
        lead_personality=content.personalities[0],
        second_personality=content.personalities[1],
        lead_angle=content.angles[0],
        second_angle=content.angles[1],
        created_at=now,
    )


def _kept_show(row: PodcastShow) -> KeptShow:
    content = ShowContent.ready_made(row.template_id) if row.template_id else _content(row)
    ref = ShowRef(template_id=row.template_id) if row.template_id else ShowRef(saved_show_id=row.id)
    return KeptShow(
        show_row_id=row.id,
        ref=ref,
        source=content.source,
        title=content.title,
        premise=content.premise,
        topic=content.topic,
        learner_role=content.learner_role,
        personalities=content.personalities,
        angles=content.angles,
        is_favourite=row.favourited_at is not None,
        last_played_at=row.last_played_at,
    )


def _content(row: PodcastShow) -> ShowContent:
    return ShowContent(
        source=row.source,
        template_id=None,
        title=row.title,
        premise=row.premise,
        topic=row.topic,
        learner_role=row.learner_role,
        personalities=(row.lead_personality, row.second_personality),
        angles=(row.lead_angle, row.second_angle),
    )


def _latest_activity(row: PodcastShow) -> datetime:
    times = [_naive(value) for value in (row.last_played_at, row.favourited_at) if value]
    return max(times, default=_NEVER)


def _naive(value: datetime) -> datetime:
    """SQLite hands back naive times; a value set in this session may still carry its zone."""
    return value.replace(tzinfo=None)


def _drop_if_unkept(db: Session, row: PodcastShow) -> bool:
    """Delete the show's row when nothing keeps it any more (data-model §2.1)."""
    is_played_learner_made = row.template_id is None and row.last_played_at is not None
    if row.favourited_at is not None or is_played_learner_made or _has_series(db, row.id):
        return False
    db.delete(row)
    return True


def _has_series(db: Session, show_row_id: int) -> bool:
    return (
        db.query(PodcastSeries.id).filter(PodcastSeries.show_id == show_row_id).first() is not None
    )


def _series_record(db: Session, row: PodcastSeries) -> SeriesRecord:
    hosts = (
        db.query(PodcastSeriesHost)
        .filter(PodcastSeriesHost.series_id == row.id)
        .order_by(PodcastSeriesHost.slot != LEAD_SLOT)
        .all()
    )
    return SeriesRecord(
        series_id=row.id,
        show=_kept_show(db.get(PodcastShow, row.show_id)),
        language=row.target_language,
        hosts=tuple(_series_host(host) for host in hosts),
        episode_count=_episode_count(db, row.id),
        unfinished=_unfinished(db, row.id),
    )


def _episode_count(db: Session, series_id: int) -> int:
    return (
        db.query(func.count(PodcastSeriesEpisode.conversation_id))
        .filter(PodcastSeriesEpisode.series_id == series_id)
        .scalar()
    )


def _unfinished(db: Session, series_id: int) -> EpisodeRef | None:
    """The latest series episode, while its conversation is still active (research R4)."""
    latest = (
        db.query(PodcastSeriesEpisode, Conversation.status)
        .join(Conversation, Conversation.id == PodcastSeriesEpisode.conversation_id)
        .filter(PodcastSeriesEpisode.series_id == series_id)
        .order_by(
            PodcastSeriesEpisode.episode_number.desc(), PodcastSeriesEpisode.conversation_id.desc()
        )
        .first()
    )
    if latest is None or latest[1] != ConversationStatus.ACTIVE:
        return None
    return EpisodeRef(latest[0].conversation_id, latest[0].episode_number)


def _series_host(row: PodcastSeriesHost) -> SeriesHost:
    return SeriesHost(
        slot=row.slot,
        name=row.name,
        personality_id=row.personality,
        voice_key=row.voice_key,
        show_role=row.show_role,
        angle=row.angle,
        joined_after_episodes=row.joined_after_episodes,
    )


def _new_series_host_row(series_id: int, host: SeriesHost, joined: int) -> PodcastSeriesHost:
    row = PodcastSeriesHost(series_id=series_id, joined_after_episodes=joined)
    _copy_host(host, row)
    return row


def _copy_host(host: SeriesHost, row: PodcastSeriesHost) -> None:
    row.slot = host.slot
    row.name = host.name
    row.personality = host.personality_id
    row.voice_key = host.voice_key
    row.show_role = host.show_role
    row.angle = host.angle


def _remembered_point(memory: PodcastSeriesMemory, episode_number: int) -> RememberedPoint:
    return RememberedPoint(
        point_id=memory.id,
        kind=memory.kind,
        conversation_language=memory.conversation_language,
        english=memory.english,
        episode_number=episode_number,
    )
