"""EpisodeTurns: one host line end to end, as `_RoleplayContext` does for a roleplay reply.

The policy picks the speaker and the purpose; the engine asks the model for that host's line;
the sanitiser keeps only that host's words; the line is stored before its frame is sent; and it
is spoken in the host's own voice (research R2–R4, R7, plan interpretation 14).
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from app.conversation_levels import ConversationLevel
from app.conversation_turns import (
    Corrections,
    EngineTurn,
    LearnerMessageRequest,
    plan_learner_turn,
    save_learner_message,
    schedule_speech,
    sse,
    start_warming,
)
from app.corrections.services.storage import CorrectionStorageProvider
from app.podcasts.services.cues import episode_history, line_turn_id, next_turn_history
from app.podcasts.services.episodes import LoadedEpisode, load_episode, turn_actions
from app.podcasts.services.sanitiser import LineSanitiser, SanitisedLine
from app.podcasts.services.speaker_views import host_voice_unavailable_message
from app.podcasts.services.storage import LineRecord, NewHostLine, PodcastStorage
from app.podcasts.services.turn_policy import SIGN_OFF, EpisodeState, LineCue, Turn, TurnPolicy
from app.services.conversation import ConversationEngine, SessionCapableProvider, TurnRequest
from app.services.llm.base import LLMError
from app.services.storage.base import StorageProvider
from app.services.tts.base import VoiceUnavailable
from app.services.tts.selection import SpeechForLanguage

logger = logging.getLogger(__name__)

EMPTY_LINE_MESSAGE = "The host's line came out empty. Press Retry to try again."
SESSION_WARMING, SESSION_LIVE = "warming", "live"
LINE_WRITING_ATTEMPTS = 2
"""An empty line is written again once (research R4)."""

CueChooser = Callable[[EpisodeState], LineCue]


class EmptyLineError(LLMError):
    """The model's line held nothing but other speakers' words, twice."""

    def __init__(self) -> None:
        super().__init__("empty host line after sanitising", EMPTY_LINE_MESSAGE)


@dataclass(frozen=True)
class EpisodeDependencies:
    podcasts: PodcastStorage
    conversations: StorageProvider
    correction_storage: CorrectionStorageProvider
    engine: ConversationEngine
    provider: SessionCapableProvider
    speech: SpeechForLanguage
    policy: TurnPolicy
    level: ConversationLevel


@dataclass(frozen=True)
class _WrittenLine:
    cue: LineCue
    sanitised: SanitisedLine


class EpisodeTurns:
    def __init__(self, deps: EpisodeDependencies, conversation_id: int) -> None:
        self._deps = deps
        self._conversation_id = conversation_id

    @property
    def conversation_id(self) -> int:
        return self._conversation_id

    def load(self) -> LoadedEpisode | None:
        pause = self._deps.correction_storage.get_pause_state(self._conversation_id)
        return load_episode(self._deps.podcasts, self._conversation_id, pause.awaiting_retry)

    def turn(self, episode: LoadedEpisode) -> Turn:
        return self._deps.policy.turn(episode.state)

    def warm(self, episode: LoadedEpisode) -> str:
        """Start the episode's session in the background, unless it is already live."""
        if self._deps.engine.is_live(episode.key):
            return SESSION_LIVE
        history = episode_history(episode.facts, episode.cast, episode.learner_label)
        prompt = episode.standing_prompt(self._deps.level)
        start_warming(self._deps.engine, self._deps.provider, episode.key, prompt, history)
        return SESSION_WARMING

    async def next_line_events(self) -> AsyncIterator[str]:
        async for frame in self._line_events(self._deps.policy.next_cue, guidance=None):
            yield frame

    async def end_events(self) -> AsyncIterator[str]:
        async for frame in self._line_events(self._deps.policy.end_cue, guidance=None):
            yield frame

    async def learner_events(
        self, req: LearnerMessageRequest, corrections: Corrections
    ) -> AsyncIterator[str]:
        """Save the learner's line, correct it as chat does, then let a host respond (FR-016)."""
        conversations, conversation_id = self._deps.conversations, self._conversation_id
        learner_message = save_learner_message(conversations, conversation_id, req)
        yield sse({"event": "user_message_saved", "message_id": learner_message.id})
        conversation = conversations.get_conversation(conversation_id)
        preceding = conversations.get_messages(conversation_id)[:-1]
        plan = await plan_learner_turn(corrections, conversation, learner_message, preceding)
        feedback = corrections.feedback_frame(conversation_id, learner_message.id, plan)
        if feedback:
            yield feedback
        if not plan.generate_reply:
            yield self._done_frame(self.load())
            return
        async for frame in self._line_events(self._deps.policy.next_cue, plan.reply_prompt_suffix):
            yield frame

    async def _line_events(self, choose: CueChooser, guidance: str | None) -> AsyncIterator[str]:
        episode = self.load()
        try:
            written = await self._write_line(episode, choose(episode.state), guidance)
        except LLMError as exc:
            yield sse({"error": exc.user_message})
            return
        line = await self._store(episode, written)
        after = self._after(episode, written.cue, line)
        self._speak(after, line)
        yield sse({"event": "line", "line": line_payload(line), **_turn_fields(self.turn(after))})
        yield self._done_frame(after)

    async def _write_line(
        self, episode: LoadedEpisode, cue: LineCue, guidance: str | None
    ) -> _WrittenLine:
        turn = EngineTurn(
            self._deps.engine, self._deps.provider, self._request(episode, cue, guidance)
        )
        sanitiser = _sanitiser_for(episode, cue)
        loop = asyncio.get_running_loop()
        for _attempt in range(LINE_WRITING_ATTEMPTS):
            tokens = await loop.run_in_executor(None, turn.collect)
            sanitised = sanitiser.clean("".join(tokens))
            if sanitised.text:
                return _WrittenLine(cue, sanitised)
        self._deps.engine.end(episode.key)
        raise EmptyLineError()

    def _request(self, episode: LoadedEpisode, cue: LineCue, guidance: str | None) -> TurnRequest:
        history = next_turn_history(episode.facts, episode.cast, episode.learner_label, cue)
        prompt = episode.standing_prompt(self._deps.level)
        return TurnRequest(episode.key, prompt, history, guidance, opening_instruction=None)

    async def _store(self, episode: LoadedEpisode, written: _WrittenLine) -> LineRecord:
        host = episode.host(written.cue.speaker_slot)
        line = self._deps.podcasts.save_host_line(
            NewHostLine(
                conversation_id=episode.conversation_id,
                host_id=host.host_id,
                content=written.sanitised.text,
                intent=written.cue.intent,
                invites_learner=written.cue.invites_learner,
                was_trimmed=written.sanitised.was_trimmed,
            )
        )
        await self._acknowledge(episode, line, written.sanitised.was_trimmed)
        return line

    async def _acknowledge(self, episode: LoadedEpisode, line: LineRecord, was_trimmed: bool):
        """Tell the session its line's id. A trimmed line ends the session: its context holds
        words that were never stored, and the saved history is the source of truth (R3)."""
        engine, turn_id = self._deps.engine, line_turn_id(line.message_id)
        await asyncio.get_running_loop().run_in_executor(
            None, engine.acknowledge, episode.key, turn_id
        )
        if was_trimmed:
            engine.end(episode.key)

    def _after(self, episode: LoadedEpisode, cue: LineCue, line: LineRecord) -> LoadedEpisode:
        """The episode after the new line, without reading storage again."""
        after = episode.with_line(line)
        if cue.intent != SIGN_OFF:
            return after
        self._deps.conversations.complete_conversation(episode.conversation_id)
        self._deps.engine.end(episode.key)
        return after.finished()

    def _speak(self, episode: LoadedEpisode, line: LineRecord) -> None:
        """Read the line aloud in its host's voice, or leave it as text and say why once."""
        host = episode.host_by_id(line.host.host_id)
        message = host_voice_unavailable_message(host.name)
        language = episode.record.target_language
        try:
            tts = self._deps.speech.provider_for_voice(language, host.voice_key, message)
        except VoiceUnavailable:
            logger.warning("%s's voice isn't installed; the line is not read aloud", host.name)
            return
        loop = asyncio.get_running_loop()
        schedule_speech(loop, self._deps.conversations, tts, line.message_id, line.content)

    def _done_frame(self, episode: LoadedEpisode) -> str:
        turn = self.turn(episode)
        return sse({"done": True, **_turn_fields(turn), **turn_actions(episode.format, turn)})


def line_payload(line: LineRecord) -> dict:
    """A line as frames and `GET /episodes/{id}` carry it (contracts §6)."""
    host = line.host
    return {
        "message_id": line.message_id,
        "speaker": "host" if host is not None else "learner",
        "host_id": host.host_id if host is not None else None,
        "content": line.content,
        "intent": host.intent if host is not None else None,
        "invites_learner": host.invites_learner if host is not None else False,
        "is_revealed": host.is_revealed if host is not None else True,
        "created_at": line.created_at.isoformat(),
    }


def _turn_fields(turn: Turn) -> dict:
    return {"turn": turn.turn, "awaiting": turn.awaiting}


def _sanitiser_for(episode: LoadedEpisode, cue: LineCue) -> LineSanitiser:
    speaker = episode.host(cue.speaker_slot).name
    others = tuple(host.name for host in episode.hosts if host.name != speaker)
    language = episode.record.target_language
    return LineSanitiser.for_speaker(speaker, others, episode.record.learner_name, language)
