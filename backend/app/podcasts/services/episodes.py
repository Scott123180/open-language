"""LoadedEpisode: one episode as stored, and everything derived from it for a turn."""

from dataclasses import dataclass, replace

from app.conversation_levels import ConversationLevel
from app.podcasts.catalog import EPISODE_LENGTHS, PODCAST_FORMATS, EpisodeLength, PodcastFormat
from app.podcasts.prompts import ShowBrief, build_standing_prompt, learner_label_for
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.storage import (
    EpisodeRecord,
    HostRecord,
    LineRecord,
    PodcastStorage,
)
from app.podcasts.services.turn_policy import LEARNER, EpisodeState, LineFacts, Turn
from app.practice_languages import ConversationLanguages
from app.services.conversation import SessionKey, SessionKind

COMPLETED_STATUS = "completed"


@dataclass(frozen=True)
class LoadedEpisode:
    record: EpisodeRecord
    hosts: tuple[HostRecord, ...]
    lines: tuple[LineRecord, ...]
    is_awaiting_retry: bool = False

    @property
    def conversation_id(self) -> int:
        return self.record.conversation_id

    @property
    def format(self) -> PodcastFormat:
        return PODCAST_FORMATS[self.record.format]

    @property
    def length(self) -> EpisodeLength:
        return EPISODE_LENGTHS[self.record.length]

    @property
    def is_finished(self) -> bool:
        return self.record.status == COMPLETED_STATUS

    @property
    def key(self) -> SessionKey:
        return SessionKey(SessionKind.PODCAST, str(self.conversation_id))

    @property
    def cast(self) -> Cast:
        hosts = {host.slot: _host(host) for host in self.hosts}
        return Cast.for_format(self.format, hosts["lead"], hosts.get("second"))

    @property
    def learner_label(self) -> str:
        return learner_label_for(self.format, self.record.learner_name)

    @property
    def languages(self) -> ConversationLanguages:
        return ConversationLanguages.of(self.record.target_language, self.record.native_language)

    @property
    def facts(self) -> tuple[LineFacts, ...]:
        slots = {host.host_id: host.slot for host in self.hosts}
        return tuple(_line_facts(line, slots) for line in self.lines)

    @property
    def state(self) -> EpisodeState:
        return EpisodeState(
            format=self.format,
            length=self.length,
            cast=self.cast,
            lines=self.facts,
            is_finished=self.is_finished,
            is_awaiting_retry=self.is_awaiting_retry,
        )

    def host(self, slot: str) -> HostRecord:
        return next(host for host in self.hosts if host.slot == slot)

    def host_by_id(self, host_id: int) -> HostRecord:
        return next(host for host in self.hosts if host.host_id == host_id)

    def standing_prompt(self, level: ConversationLevel) -> str:
        show = ShowBrief(
            self.record.title, self.record.premise, self.record.topic, self.record.learner_role
        )
        return build_standing_prompt(show, self.cast, self.learner_label, self.languages, level)

    def with_line(self, line: LineRecord) -> "LoadedEpisode":
        return replace(self, lines=(*self.lines, line))

    def finished(self) -> "LoadedEpisode":
        return replace(self, record=replace(self.record, status=COMPLETED_STATUS))


def load_episode(
    podcasts: PodcastStorage, conversation_id: int, is_awaiting_retry: bool = False
) -> LoadedEpisode | None:
    record = podcasts.get_episode(conversation_id)
    if record is None:
        return None
    hosts = podcasts.get_hosts(conversation_id)
    lines = podcasts.get_lines(conversation_id)
    return LoadedEpisode(record, hosts, lines, is_awaiting_retry)


def turn_actions(podcast_format: PodcastFormat, turn: Turn) -> dict[str, bool]:
    """Which secondary actions the turn allows: Jump in at the hosts' Continue, Pass at the
    learner's turn, both only in a format with Jump in (FR-017)."""
    return {
        "can_jump_in": podcast_format.has_jump_in and turn.awaiting == "continue",
        "can_pass": podcast_format.has_jump_in and turn.turn == "learner",
    }


def _host(record: HostRecord) -> Host:
    return Host(
        record.slot,
        record.name,
        record.personality_id,
        record.voice_key,
        record.show_role,
        record.angle,
    )


def _line_facts(line: LineRecord, slots: dict[int, str]) -> LineFacts:
    if line.host is None:
        return LineFacts(LEARNER, None, text=line.content, message_id=line.message_id)
    return LineFacts(
        speaker=slots[line.host.host_id],
        intent=line.host.intent,
        invites_learner=line.host.invites_learner,
        is_passed=line.host.is_passed,
        text=line.content,
        message_id=line.message_id,
    )
