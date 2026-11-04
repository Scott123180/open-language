"""LineWriter: one host line, streamed from the model as kept sentences (011 research R13).

Tokens come from the engine's live stream on a worker thread, are cut into sentences, and each
sentence is sanitised as it completes. A line cut or empty before its first kept sentence is
written again, invisibly, since nothing was sent yet. Once a sentence has been given, a failure
loses the line: the caller stores nothing and tells the learner to retry.
"""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from app.conversation_turns import iterate_in_thread
from app.podcasts.services.sanitiser import StreamingSanitiser
from app.podcasts.services.sentences import SentenceSplitter
from app.services.conversation import ConversationEngine, SessionCapableProvider, TurnRequest
from app.services.llm.base import LLMError

EMPTY_LINE_MESSAGE = "The host's line came out empty. Press Retry to try again."
LINE_LOST_MESSAGE = "The host lost their words. Press Retry."
LINE_WRITING_ATTEMPTS = 2
"""An empty line is written again once (007 research R4)."""


class EmptyLineError(LLMError):
    """The model's line held nothing but other speakers' words, twice."""

    def __init__(self) -> None:
        super().__init__("empty host line after sanitising", EMPTY_LINE_MESSAGE)


class LineLostError(LLMError):
    """The line failed after some of it was sent: the client drops what arrived."""

    def __init__(self, stream_id: str) -> None:
        super().__init__(f"host line {stream_id} failed part-way", LINE_LOST_MESSAGE)
        self.stream_id = stream_id


@dataclass(frozen=True, slots=True)
class LineRequest:
    turn: TurnRequest
    sanitiser: Callable[[], StreamingSanitiser]
    """A fresh sanitiser for each attempt at the line."""
    stream_id: str


@dataclass(frozen=True, slots=True)
class KeptSentence:
    text: str


@dataclass(frozen=True, slots=True)
class WrittenLine:
    text: str
    """The kept sentences joined by single spaces, with no address tag."""
    was_trimmed: bool
    addressee: str | None
    is_address_from_tag: bool


class LineWriter:
    def __init__(self, engine: ConversationEngine, provider: SessionCapableProvider) -> None:
        self._engine = engine
        self._provider = provider

    async def write(self, line: LineRequest) -> AsyncIterator[KeptSentence | WrittenLine]:
        """Each kept sentence as it completes, then the whole line."""
        for _attempt in range(LINE_WRITING_ATTEMPTS):
            async for event in self._attempt(line):
                yield event
                if isinstance(event, WrittenLine):
                    return
        self._engine.end(line.turn.key)
        raise EmptyLineError()

    async def _attempt(self, line: LineRequest) -> AsyncIterator[KeptSentence | WrittenLine]:
        """One try at the line; it gives nothing if nothing of it is kept."""
        sanitiser, kept = line.sanitiser(), []
        tokens = iterate_in_thread(lambda: self._engine.stream_live(self._provider, line.turn))
        try:
            async for sentence in _kept_sentences(tokens, sanitiser):
                kept.append(sentence)
                yield KeptSentence(sentence)
        except LLMError as exc:
            if kept:
                raise LineLostError(line.stream_id) from exc
            raise
        finally:
            await tokens.aclose()
        if kept:
            address = sanitiser.address()
            text = " ".join(kept)
            yield WrittenLine(text, sanitiser.was_trimmed, address.addressee, address.is_from_tag)


async def _kept_sentences(tokens: AsyncIterator[str], sanitiser: StreamingSanitiser):
    """The sentences the sanitiser keeps, until another speaker's words begin."""
    splitter = SentenceSplitter()
    async for token in tokens:
        for sentence in splitter.feed(token):
            verdict = sanitiser.clean_sentence(sentence)
            if verdict.text:
                yield verdict.text
            if verdict.is_cut:
                return
    rest = splitter.flush()
    verdict = sanitiser.clean_sentence(rest) if rest else None
    if verdict is not None and verdict.text:
        yield verdict.text
