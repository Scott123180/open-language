"""What a series' hosts remember, written in the background (010 research R6, R7).

`SeriesMemoryKeeper` reads each series episode's unread lines in chunks, with one structured
call per chunk, and writes what was found. Learner points are kept only from a chunk that holds
learner lines, so a Listen episode adds topics only. `MemoryCatchUps` runs one catch-up per
series at a time and holds no keeper or provider: each catch-up runs on the keeper of the
request that started it, so a provider switched on Settings applies to the next one.
"""

import json
import logging
import threading
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import Executor
from contextlib import AbstractContextManager
from dataclasses import dataclass, field

from app.podcasts.catalog import (
    MAX_POINTS_PER_EPISODE,
    MEMORY_CHUNK_CHARACTERS,
    REMEMBERED_POINT_MAX_LENGTH,
)
from app.podcasts.prompts import LEARNER_SPEAKER, MEMORY_JSON_SCHEMA, memory_prompt
from app.podcasts.services.episode_endings import EpisodeEndings
from app.podcasts.services.series_storage import (
    MemoryReply,
    PendingEpisode,
    PointText,
    SeriesStorage,
)
from app.podcasts.services.storage import LineRecord, PodcastStorage
from app.practice_languages import ConversationLanguages
from app.services.llm.base import ChatMessage, LLMError, StructuredLLMProvider

logger = logging.getLogger(__name__)

UNREADABLE_MEMORY = "The hosts' notes came back unreadable. Please try again."
CATCH_UP_FAILED = "The hosts couldn't catch up this time. Please try again."
TIMED_OUT_DETAIL = "It's taking longer than usual."
STARTED, RUNNING, UP_TO_DATE, PENDING = "started", "running", "up_to_date", "pending"
FAILED, TIMED_OUT = "failed", "timed_out"
USER_ROLE = "user"


class UnreadableMemoryError(LLMError):
    """The memory reply could not be read. Logged; the catch-up is tried again later."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, UNREADABLE_MEMORY)


def parse_memory_reply(raw: str) -> MemoryReply:
    """The reply's topic and at most three learner points, trimmed and cut to length."""
    try:
        parsed = json.loads(raw)
        topic = _point(parsed["topic"]) if parsed["topic"] is not None else None
        learner = [_point(item) for item in parsed["about_learner"]]
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise UnreadableMemoryError(f"malformed memory reply: {exc}") from exc
    kept = tuple(point for point in learner if point is not None)
    return MemoryReply(topic, kept[:MAX_POINTS_PER_EPISODE])


def _point(item: dict) -> PointText | None:
    """A point in both languages, or None when the model left it blank."""
    conversation_language = _cut(item["conversation_language"])
    english = _cut(item["english"])
    if not conversation_language or not english:
        return None
    return PointText(conversation_language, english)


def _cut(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError(f"a point's text must be a string, not {value!r}")
    return value.strip()[:REMEMBERED_POINT_MAX_LENGTH].strip()


@dataclass(frozen=True)
class MemoryStores:
    podcasts: PodcastStorage
    series: SeriesStorage


StoresFactory = Callable[[], AbstractContextManager[MemoryStores]]
"""Opens the keeper's own storage, apart from any request's: it runs in the background."""


@dataclass(frozen=True)
class TranscriptChunk:
    lines: tuple[str, ...]
    last_message_id: int
    has_learner_lines: bool

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def fold_lines(lines: Sequence[LineRecord], names: dict[int, str]) -> list[TranscriptChunk]:
    """Labelled lines, folded into chunks of at most MEMORY_CHUNK_CHARACTERS (007 R14)."""
    chunks: list[list[LineRecord]] = [[]]
    size = 0
    for line in lines:
        labelled = len(_labelled(line, names)) + 1
        if chunks[-1] and size + labelled > MEMORY_CHUNK_CHARACTERS:
            chunks.append([])
            size = 0
        chunks[-1].append(line)
        size += labelled
    return [_chunk(chunk, names) for chunk in chunks if chunk]


def _chunk(lines: list[LineRecord], names: dict[int, str]) -> TranscriptChunk:
    return TranscriptChunk(
        lines=tuple(_labelled(line, names) for line in lines),
        last_message_id=lines[-1].message_id,
        has_learner_lines=any(line.host is None for line in lines),
    )


def _labelled(line: LineRecord, names: dict[int, str]) -> str:
    speaker = names[line.host.host_id] if line.host is not None else LEARNER_SPEAKER
    return f"{speaker}: {line.content}"


class SeriesMemoryKeeper:
    def __init__(self, structured_llm: StructuredLLMProvider, stores: StoresFactory) -> None:
        self._llm = structured_llm
        self._stores = stores

    def catch_up(self, series_id: int) -> None:
        """Remember every pending episode's unread lines. A provider error is logged and
        raised, leaving the episode's marker where it was."""
        with self._stores() as stores:
            for pending in stores.series.pending_episodes(series_id):
                try:
                    self._remember_episode(stores, series_id, pending)
                except LLMError as error:
                    episode = pending.conversation_id
                    logger.warning(
                        "Series %s could not remember episode %s: %s", series_id, episode, error
                    )
                    raise

    def _remember_episode(self, stores: MemoryStores, series_id: int, pending: PendingEpisode):
        conversation_id = pending.conversation_id
        record = stores.podcasts.get_episode(conversation_id)
        names = {host.host_id: host.name for host in stores.podcasts.get_hosts(conversation_id)}
        unread = _unread(stores.podcasts.get_lines(conversation_id), pending)
        languages = ConversationLanguages.of(record.target_language, record.native_language)
        for chunk in fold_lines(unread, names):
            remembered = [p.conversation_language for p in stores.series.remembered(series_id)]
            reply = self._ask(chunk, tuple(names.values()), remembered, languages)
            stores.series.remember(series_id, conversation_id, reply, chunk.last_message_id)

    def _ask(
        self,
        chunk: TranscriptChunk,
        host_names: tuple[str, ...],
        remembered: list[str],
        languages: ConversationLanguages,
    ) -> MemoryReply:
        prompt = memory_prompt(chunk.text, host_names, remembered, languages)
        raw = self._llm.chat_json([ChatMessage(USER_ROLE, prompt)], MEMORY_JSON_SCHEMA)
        reply = parse_memory_reply(raw)
        if chunk.has_learner_lines:
            return reply
        return MemoryReply(reply.topic, ())


def _unread(lines: Iterable[LineRecord], pending: PendingEpisode) -> list[LineRecord]:
    marker = pending.remembered_up_to_message_id
    return [line for line in lines if marker is None or line.message_id > marker]


@dataclass(frozen=True)
class CatchUpOutcome:
    status: str
    detail: str | None = None


@dataclass
class _CatchUp:
    finished: threading.Event = field(default_factory=threading.Event)
    failure: str | None = None


class MemoryCatchUps:
    """One catch-up per series at a time, process-wide. Holds no keeper or provider."""

    def __init__(self, executor: Executor) -> None:
        self._executor = executor
        self._running: dict[int, _CatchUp] = {}
        self._guard = threading.Lock()

    def start(self, series_id: int, keeper: SeriesMemoryKeeper) -> str:
        """Start a catch-up on `keeper`, unless one is already running for the series."""
        _catch_up, is_new = self._claim(series_id, keeper)
        return STARTED if is_new else RUNNING

    def status(self, series_id: int, series: SeriesStorage) -> str:
        """Derived, never stored (data-model §5.3)."""
        if self.is_running(series_id):
            return RUNNING
        return PENDING if series.pending_episodes(series_id) else UP_TO_DATE

    def is_running(self, series_id: int) -> bool:
        with self._guard:
            return series_id in self._running

    def wait(self, series_id: int, keeper: SeriesMemoryKeeper, limit: float) -> CatchUpOutcome:
        """Start a catch-up if none runs, then wait for it, at most `limit` seconds."""
        catch_up, _is_new = self._claim(series_id, keeper)
        if not catch_up.finished.wait(limit):
            return CatchUpOutcome(TIMED_OUT, TIMED_OUT_DETAIL)
        if catch_up.failure is not None:
            return CatchUpOutcome(FAILED, catch_up.failure)
        return CatchUpOutcome(UP_TO_DATE)

    def _claim(self, series_id: int, keeper: SeriesMemoryKeeper) -> tuple[_CatchUp, bool]:
        with self._guard:
            running = self._running.get(series_id)
            if running is not None:
                return running, False
            catch_up = self._running[series_id] = _CatchUp()
        self._executor.submit(self._run, series_id, keeper, catch_up)
        return catch_up, True

    def _run(self, series_id: int, keeper: SeriesMemoryKeeper, catch_up: _CatchUp) -> None:
        try:
            keeper.catch_up(series_id)
        except LLMError as error:
            logger.warning("Series %s memory catch-up stopped: %s", series_id, error)
            catch_up.failure = error.user_message
        except Exception:
            logger.exception("Series %s memory catch-up failed unexpectedly", series_id)
            catch_up.failure = CATCH_UP_FAILED
        finally:
            with self._guard:
                self._running.pop(series_id, None)
            catch_up.finished.set()


class KeeperEndings(EpisodeEndings):
    """After a series episode signs off, its series catches up on it (research R6)."""

    def __init__(
        self, catch_ups: MemoryCatchUps, podcasts: PodcastStorage, keeper: SeriesMemoryKeeper
    ) -> None:
        self._catch_ups = catch_ups
        self._podcasts = podcasts
        self._keeper = keeper

    def episode_finished(self, conversation_id: int) -> None:
        record = self._podcasts.get_episode(conversation_id)
        if record is not None and record.series is not None:
            self._catch_ups.start(record.series.series_id, self._keeper)
