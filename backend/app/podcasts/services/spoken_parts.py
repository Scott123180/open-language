"""SpokenParts: a streamed host line, spoken one sentence at a time (011 research R13.5–R13.6).

Each kept sentence is synthesised in the host's voice on one worker, so parts come out in order,
into `tts_cache/parts/{stream_id}-{n}.wav`. The client fetches each part by its URL as it plays.
Once the line is stored, the parts are joined into the line's own WAV, so Replay and Slower use
the existing audio endpoint and nothing is synthesised twice. Process-wide, built once in the
factory; a stream is forgotten `PART_TTL_SECONDS` after its line ends.
"""

import threading
import wave
from collections.abc import Callable
from concurrent.futures import Executor, Future
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from pathlib import Path

from app.podcasts.catalog import PART_TTL_SECONDS, PART_WAIT_SECONDS
from app.services.tts.base import TTSError, TTSProvider, VoiceUnavailable

PARTS_FOLDER = "parts"
PART_URL = "/api/podcasts/episodes/{conversation_id}/parts/{stream_id}/{index}"


class PartNotFound(LookupError):  # noqa: N818 — reads as what the learner is told
    """No such part: an unknown or expired stream, an unknown index, or another episode's."""


class PartTimedOut(TimeoutError):  # noqa: N818 — reads as what happened
    """The part was not spoken in time."""


@dataclass(frozen=True, slots=True)
class LinePart:
    stream_id: str
    index: int
    text: str
    audio_url: str | None
    """None when the host's voice is not installed: the line stays text (007 FR-031)."""


@dataclass
class _Stream:
    conversation_id: int
    tts: TTSProvider | None
    unavailable_message: str
    """What the learner is told if the host's voice stops working (007 FR-031)."""
    parts: list[tuple[Path, Future | None]] = field(default_factory=list)
    ended_at: float | None = None


class SpokenParts:
    def __init__(
        self,
        worker: Executor,
        clock: Callable[[], float],
        cache_dir: Path,
        wait_seconds: float = PART_WAIT_SECONDS,
    ) -> None:
        """`worker` speaks one part at a time; `cache_dir` is the speech cache; `wait_seconds`
        is how long joining the line waits for each part."""
        self._worker = worker
        self._wait_seconds = wait_seconds
        self._clock = clock
        self._cache_dir = cache_dir
        self._streams: dict[str, _Stream] = {}
        self._lock = threading.Lock()
        self._is_open = True

    def begin(
        self,
        stream_id: str,
        conversation_id: int,
        tts: TTSProvider | None,
        unavailable_message: str,
    ) -> None:
        """Start a line's stream; `tts` is None when the host's voice is missing."""
        self._remove_expired()
        with self._lock:
            self._streams[stream_id] = _Stream(conversation_id, tts, unavailable_message)

    def add(self, stream_id: str, text: str) -> LinePart:
        """Queue one sentence for speech, and say where its audio will be."""
        with self._lock:
            stream = self._streams[stream_id]
            index = len(stream.parts)
            path = self._cache_dir / PARTS_FOLDER / f"{stream_id}-{index}.wav"
            spoken = self._speak(stream.tts, text, path)
            stream.parts.append((path, spoken))
        if spoken is None:
            return LinePart(stream_id, index, text, None)
        url = PART_URL.format(
            conversation_id=stream.conversation_id, stream_id=stream_id, index=index
        )
        return LinePart(stream_id, index, text, url)

    def audio(self, conversation_id: int, stream_id: str, index: int, timeout: float) -> Path:
        """The part's WAV once spoken. Raises PartNotFound, PartTimedOut or VoiceUnavailable."""
        stream, path, spoken = self._part(conversation_id, stream_id, index)
        try:
            spoken.result(timeout=timeout)
        except FutureTimeout as late:
            raise PartTimedOut() from late
        except TTSError as failed:
            raise VoiceUnavailable(stream.unavailable_message) from failed
        return path

    def assemble(self, stream_id: str, message_id: int) -> Path | None:
        """Join the line's parts into its own WAV; None when it was not all spoken in time,
        so the line is spoken whole when it is first replayed."""
        with self._lock:
            stream = self._streams[stream_id]
            stream.ended_at = self._clock()
        if stream.tts is None or not stream.parts or not self._all_spoken(stream):
            return None
        line_audio = self._cache_dir / f"{message_id}.wav"
        _join([path for path, _spoken in stream.parts], line_audio)
        return line_audio

    @property
    def is_open(self) -> bool:
        return self._is_open

    def close(self) -> None:
        """Stop the speaking worker, when the app shuts down."""
        self._is_open = False
        self._worker.shutdown(wait=False, cancel_futures=True)

    def discard(self, stream_id: str) -> None:
        """Forget a lost line's stream and remove its parts."""
        with self._lock:
            stream = self._streams.pop(stream_id, None)
        if stream is not None:
            _remove_files([stream])

    def _all_spoken(self, stream: _Stream) -> bool:
        try:
            for _path, spoken in stream.parts:
                spoken.result(timeout=self._wait_seconds)
        except (FutureTimeout, TTSError):
            return False
        return True

    def _speak(self, tts: TTSProvider | None, text: str, path: Path) -> Future | None:
        if tts is None:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        return self._worker.submit(tts.synthesize, text, path)

    def _part(
        self, conversation_id: int, stream_id: str, index: int
    ) -> tuple[_Stream, Path, Future]:
        self._remove_expired()
        with self._lock:
            stream = self._streams.get(stream_id)
        if stream is None or stream.conversation_id != conversation_id:
            raise PartNotFound()
        if not 0 <= index < len(stream.parts) or stream.parts[index][1] is None:
            raise PartNotFound()
        return stream, *stream.parts[index]

    def _remove_expired(self) -> None:
        _remove_files(self._sweep())

    def _sweep(self) -> list[_Stream]:
        """Forget every stream whose line ended more than `PART_TTL_SECONDS` ago."""
        cutoff = self._clock() - PART_TTL_SECONDS
        with self._lock:
            expired = [
                stream_id
                for stream_id, stream in self._streams.items()
                if stream.ended_at is not None and stream.ended_at < cutoff
            ]
            return [self._streams.pop(stream_id) for stream_id in expired]


def _join(paths: list[Path], output: Path) -> None:
    """One voice, so one format: the frames of every part, in order."""
    with wave.open(str(paths[0]), "rb") as first:
        params = first.getparams()
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as joined:
        joined.setparams(params)
        for path in paths:
            with wave.open(str(path), "rb") as part:
                joined.writeframes(part.readframes(part.getnframes()))


def _remove_files(streams: list[_Stream]) -> None:
    for stream in streams:
        for path, _spoken in stream.parts:
            path.unlink(missing_ok=True)
