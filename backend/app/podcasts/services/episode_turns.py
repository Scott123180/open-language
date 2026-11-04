"""EpisodeTurns: one host line end to end, as `_RoleplayContext` does for a roleplay reply.

The policy picks the speaker and the purpose; the line writer streams that host's line from the
model, sentence by sentence, keeping only that host's words; each kept sentence is sent as a
part and spoken in the host's own voice as it comes; and the whole line is stored, with who it
was for, before its `line` frame is sent (research R2–R4, R7; 011 research R13, R19).
"""

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import asdict, dataclass
from functools import partial

from app.conversation_levels import ConversationLevel
from app.conversation_turns import (
    Corrections,
    LearnerMessageRequest,
    plan_learner_turn,
    save_learner_message,
    sse,
    start_warming,
)
from app.corrections.services.storage import CorrectionStorageProvider
from app.podcasts.services.cues import episode_history, line_turn_id, next_turn_history
from app.podcasts.services.episode_endings import EpisodeEndings
from app.podcasts.services.episodes import LoadedEpisode, load_episode, turn_actions
from app.podcasts.services.line_address import LineAddress
from app.podcasts.services.line_writer import (
    LineLostError,
    LineRequest,
    LineWriter,
    WrittenLine,
)
from app.podcasts.services.sanitiser import LineSanitiser, StreamingSanitiser
from app.podcasts.services.speaker_views import host_voice_unavailable_message
from app.podcasts.services.spoken_parts import SpokenParts
from app.podcasts.services.storage import LineRecord, NewHostLine, PodcastStorage
from app.podcasts.services.turn_policy import SIGN_OFF, EpisodeState, LineCue, Turn, TurnPolicy
from app.services.conversation import ConversationEngine, SessionCapableProvider, TurnRequest
from app.services.llm.base import LLMError
from app.services.storage.base import StorageProvider
from app.services.tts.base import TTSProvider, VoiceUnavailable
from app.services.tts.selection import SpeechForLanguage

logger = logging.getLogger(__name__)

SESSION_WARMING, SESSION_LIVE = "warming", "live"

CueChooser = Callable[[EpisodeState], LineCue]


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
    endings: EpisodeEndings
    """Told when an episode signs off, so a series can remember it (010 research R6)."""
    writer: LineWriter
    """Streams a host line from the model as kept sentences (011 research R13)."""
    spoken: SpokenParts
    """Speaks each kept sentence, and joins them into the line's audio (011 research R13)."""


@dataclass
class _LineStream:
    """One host line on its way: its parts' stream, and the line once written."""

    stream_id: str
    has_started: bool = False
    written: WrittenLine | None = None


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
        history = episode_history(episode.facts, episode.cue_context)
        prompt = episode.standing_prompt(self._deps.level)
        start_warming(self._deps.engine, self._deps.provider, episode.key, prompt, history)
        return SESSION_WARMING

    async def next_line_events(self) -> AsyncIterator[str]:
        async for frame in self._line_events(self._deps.policy.next_cue, guidance=None):
            yield frame

    async def pass_events(self) -> AsyncIterator[str]:
        """FR-017: the learner passes on the invitation, and the hosts carry on without them."""
        invitation = self.load().lines[-1]
        self._deps.podcasts.mark_passed(invitation.message_id)
        async for frame in self.next_line_events():
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
        cue = choose(episode.state)
        stream = _LineStream(uuid.uuid4().hex)
        try:
            async for frame in self._streamed_parts(episode, cue, guidance, stream):
                yield frame
        except LLMError as exc:
            yield self._lost(episode, exc)
            return
        line = await self._store(episode, cue, stream.written)
        after = self._after(episode, cue, line)
        await self._assemble_audio(line, stream.stream_id)
        yield sse({"event": "line", "line": line_payload(line), **_turn_fields(self.turn(after))})
        yield self._done_frame(after)

    async def _streamed_parts(
        self, episode: LoadedEpisode, cue: LineCue, guidance: str | None, stream: _LineStream
    ) -> AsyncIterator[str]:
        """`line_started` before the first kept sentence, then one `line_part` per sentence."""
        sanitiser = partial(_streaming_sanitiser, episode, cue)
        request = LineRequest(self._request(episode, cue, guidance), sanitiser, stream.stream_id)
        async for event in self._deps.writer.write(request):
            if isinstance(event, WrittenLine):
                stream.written = event
                continue
            if not stream.has_started:
                yield self._started(episode, cue, stream)
            part = self._deps.spoken.add(stream.stream_id, event.text)
            yield sse({"event": "line_part", **asdict(part)})

    def _started(self, episode: LoadedEpisode, cue: LineCue, stream: _LineStream) -> str:
        host = episode.host(cue.speaker_slot)
        tts = self._host_tts(episode, host.name, host.voice_key)
        message = host_voice_unavailable_message(host.name)
        self._deps.spoken.begin(stream.stream_id, episode.conversation_id, tts, message)
        stream.has_started = True
        return sse(
            {"event": "line_started", "stream_id": stream.stream_id, "host_id": host.host_id}
        )

    def _lost(self, episode: LoadedEpisode, error: LLMError) -> str:
        """A line lost part-way ends the session and drops its parts; nothing was stored."""
        if not isinstance(error, LineLostError):
            return sse({"error": error.user_message})
        self._deps.engine.end(episode.key)
        self._deps.spoken.discard(error.stream_id)
        return sse({"error": error.user_message, "stream_id": error.stream_id})

    def _request(self, episode: LoadedEpisode, cue: LineCue, guidance: str | None) -> TurnRequest:
        history = next_turn_history(episode.facts, episode.cue_context, cue)
        prompt = episode.standing_prompt(self._deps.level)
        return TurnRequest(episode.key, prompt, history, guidance, opening_instruction=None)

    async def _store(
        self, episode: LoadedEpisode, cue: LineCue, written: WrittenLine
    ) -> LineRecord:
        line = self._deps.podcasts.save_host_line(_host_line_for(episode, cue, written))
        await self._acknowledge(episode, line, written.was_trimmed)
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
        self._deps.endings.episode_finished(episode.conversation_id)
        return after.finished()

    def _host_tts(self, episode: LoadedEpisode, name: str, voice_key: str) -> TTSProvider | None:
        """The host's own voice, or None: the line stays text, and says why once (FR-031)."""
        message = host_voice_unavailable_message(name)
        language = episode.record.target_language
        try:
            return self._deps.speech.provider_for_voice(language, voice_key, message)
        except VoiceUnavailable:
            logger.warning("%s's voice isn't installed; the line is not read aloud", name)
            return None

    async def _assemble_audio(self, line: LineRecord, stream_id: str) -> None:
        """The line's own WAV, joined from its parts, for Replay and Slower."""
        loop = asyncio.get_running_loop()
        spoken = self._deps.spoken
        audio = await loop.run_in_executor(None, spoken.assemble, stream_id, line.message_id)
        if audio is not None:
            self._deps.conversations.set_tts_path(line.message_id, str(audio))

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


def _host_line_for(episode: LoadedEpisode, cue: LineCue, written: WrittenLine) -> NewHostLine:
    """The line as stored: its invitation decided from the written line (011 research R19)."""
    talk, addressee = episode.talk, written.addressee
    ask, stored_addressee = talk.stored_addressing(cue.ask, addressee)
    return NewHostLine(
        conversation_id=episode.conversation_id,
        host_id=episode.host(cue.speaker_slot).host_id,
        content=written.text,
        intent=cue.intent,
        invites_learner=talk.invitation(cue.ask, addressee),
        was_trimmed=written.was_trimmed,
        ask=ask,
        addressee=stored_addressee,
    )


def _turn_fields(turn: Turn) -> dict:
    return {"turn": turn.turn, "awaiting": turn.awaiting}


def _streaming_sanitiser(episode: LoadedEpisode, cue: LineCue) -> StreamingSanitiser:
    is_listening = not episode.format.is_learner_speaking
    language = episode.record.target_language
    address = LineAddress.for_episode(
        episode.cast, episode.learner_label, cue.speaker_slot, language, is_listening
    )
    return StreamingSanitiser(_sanitiser_for(episode, cue), address)


def _sanitiser_for(episode: LoadedEpisode, cue: LineCue) -> LineSanitiser:
    speaker = episode.host(cue.speaker_slot).name
    others = tuple(host.name for host in episode.hosts if host.name != speaker)
    language = episode.record.target_language
    return LineSanitiser.for_speaker(speaker, others, episode.record.learner_name, language)
