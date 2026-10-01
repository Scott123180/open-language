"""PodcastStorage: what the podcast module stores about an episode, beside its conversation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class NewHost:
    slot: str
    name: str
    personality_id: str
    voice_key: str
    show_role: str
    angle: str | None = None


@dataclass(frozen=True, slots=True)
class NewEpisode:
    """Everything needed to start an episode: its conversation, show, format and hosts."""

    show_source: str
    show_id: str | None
    title: str
    premise: str
    topic: str
    learner_role: str
    format: str
    length: str
    learner_name: str | None
    target_language: str
    native_language: str
    llm_model: str
    hosts: tuple[NewHost, ...]


@dataclass(frozen=True, slots=True)
class EpisodeRecord:
    conversation_id: int
    show_source: str
    show_id: str | None
    title: str
    premise: str
    topic: str
    learner_role: str
    format: str
    length: str
    learner_name: str | None
    target_language: str
    native_language: str
    status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class HostRecord:
    host_id: int
    slot: str
    name: str
    personality_id: str
    voice_key: str
    show_role: str
    angle: str | None


@dataclass(frozen=True, slots=True)
class HostLineFacts:
    """Who spoke a host line and why. Learner lines have none."""

    host_id: int
    intent: str
    invites_learner: bool
    is_passed: bool
    is_revealed: bool
    was_trimmed: bool


@dataclass(frozen=True, slots=True)
class LineRecord:
    message_id: int
    role: str
    content: str
    created_at: datetime
    host: HostLineFacts | None

    @property
    def is_host(self) -> bool:
        return self.host is not None


@dataclass(frozen=True, slots=True)
class NewHostLine:
    conversation_id: int
    host_id: int
    content: str
    intent: str
    invites_learner: bool
    was_trimmed: bool = False


@dataclass(frozen=True, slots=True)
class PreferencesRecord:
    last_format: str
    is_show_text_on: bool
    interests: tuple[str, ...]
    learner_name: str | None


class PodcastStorage(ABC):
    @abstractmethod
    def create_episode(self, episode: NewEpisode) -> EpisodeRecord:
        """Create the conversation, the episode and its hosts together, or nothing."""

    @abstractmethod
    def get_episode(self, conversation_id: int) -> EpisodeRecord | None: ...

    @abstractmethod
    def list_episodes(self) -> list[EpisodeRecord]:
        """Every episode, most recent first."""

    @abstractmethod
    def get_hosts(self, conversation_id: int) -> tuple[HostRecord, ...]:
        """The episode's hosts, the lead first."""

    @abstractmethod
    def save_host_line(self, line: NewHostLine) -> LineRecord:
        """Store a host line as an assistant message plus who spoke it and why."""

    @abstractmethod
    def get_lines(self, conversation_id: int) -> tuple[LineRecord, ...]:
        """The episode's messages in order, each with its host facts or None for the learner."""

    @abstractmethod
    def mark_passed(self, message_id: int) -> None: ...

    @abstractmethod
    def mark_revealed(self, conversation_id: int, message_id: int) -> bool:
        """Reveal a host line of this episode. False when it is not one. Idempotent."""

    @abstractmethod
    def get_preferences(self) -> PreferencesRecord:
        """The learner's podcast preferences, created with their defaults on first read."""

    @abstractmethod
    def save_preferences(self, preferences: PreferencesRecord) -> PreferencesRecord: ...
