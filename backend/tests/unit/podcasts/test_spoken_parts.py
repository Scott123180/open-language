"""011 T033: SpokenParts, a streamed line spoken sentence by sentence (research R13.5–R13.6)."""

import wave
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

import pytest

from app.podcasts.catalog import PART_TTL_SECONDS
from app.podcasts.services.spoken_parts import (
    LinePart,
    PartNotFound,
    PartTimedOut,
    SpokenParts,
)
from tests.support.fake_speech import RecordingTtsBuilder
from tests.support.synchronous_executor import SynchronousExecutor

EPISODE = 41
STREAM = "b3f1"
VOICE = "es_ES-davefx-medium"
UNAVAILABLE = "Hugo's voice isn't installed."


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def speech() -> RecordingTtsBuilder:
    return RecordingTtsBuilder()


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def parts(tmp_path: Path, clock: Clock) -> SpokenParts:
    return SpokenParts(SynchronousExecutor(), clock, tmp_path)


def _frames(path: Path) -> int:
    with wave.open(str(path), "rb") as wav_file:
        return wav_file.getnframes()


def test_each_sentence_is_a_part_with_its_own_audio_url(parts, speech):
    parts.begin(STREAM, EPISODE, speech(VOICE), UNAVAILABLE)

    added = [parts.add(STREAM, text) for text in ("Hola a todos.", "Hoy hablamos de pan.")]

    assert added == [
        LinePart(STREAM, 0, "Hola a todos.", f"/api/podcasts/episodes/{EPISODE}/parts/{STREAM}/0"),
        LinePart(
            STREAM, 1, "Hoy hablamos de pan.", f"/api/podcasts/episodes/{EPISODE}/parts/{STREAM}/1"
        ),
    ]


def test_parts_are_spoken_in_order_into_the_parts_folder(parts, speech, tmp_path):
    parts.begin(STREAM, EPISODE, speech(VOICE), UNAVAILABLE)
    parts.add(STREAM, "Uno.")
    parts.add(STREAM, "Dos.")

    assert [(text, path) for _voice, text, path in speech.synthesized] == [
        ("Uno.", tmp_path / "parts" / f"{STREAM}-0.wav"),
        ("Dos.", tmp_path / "parts" / f"{STREAM}-1.wav"),
    ]


def test_a_parts_audio_is_its_file_once_ready(parts, speech, tmp_path):
    parts.begin(STREAM, EPISODE, speech(VOICE), UNAVAILABLE)
    parts.add(STREAM, "Uno.")

    assert parts.audio(EPISODE, STREAM, 0, timeout=1) == tmp_path / "parts" / f"{STREAM}-0.wav"


@pytest.mark.parametrize(
    ("episode", "stream", "index"),
    [(EPISODE, "unknown", 0), (EPISODE, STREAM, 5), (EPISODE + 1, STREAM, 0)],
    ids=["unknown-stream", "unknown-index", "another-episode"],
)
def test_an_unknown_part_is_not_found(parts, speech, episode, stream, index):
    parts.begin(STREAM, EPISODE, speech(VOICE), UNAVAILABLE)
    parts.add(STREAM, "Uno.")

    with pytest.raises(PartNotFound):
        parts.audio(episode, stream, index, timeout=1)


def test_a_part_not_ready_in_time_times_out(tmp_path, clock, speech):
    never: Future = Future()

    class Waiting(SynchronousExecutor):
        def submit(self, fn, /, *args, **kwargs) -> Future:
            return never

    parts = SpokenParts(Waiting(), clock, tmp_path)
    parts.begin(STREAM, EPISODE, speech(VOICE), UNAVAILABLE)
    parts.add(STREAM, "Uno.")

    with pytest.raises(PartTimedOut):
        parts.audio(EPISODE, STREAM, 0, timeout=0.01)


def test_assembling_joins_the_parts_into_the_lines_audio(parts, speech, tmp_path):
    parts.begin(STREAM, EPISODE, speech(VOICE), UNAVAILABLE)
    for text in ("Uno.", "Dos.", "Tres."):
        parts.add(STREAM, text)

    line_audio = parts.assemble(STREAM, message_id=402)

    assert line_audio == tmp_path / "402.wav"
    part_frames = sum(_frames(path) for _voice, _text, path in speech.synthesized)
    assert _frames(line_audio) == part_frames
    with (
        wave.open(str(line_audio), "rb") as joined,
        wave.open(str(speech.synthesized[0][2]), "rb") as part,
    ):
        assert joined.getparams()[:3] == part.getparams()[:3]


def test_with_the_voice_missing_nothing_is_spoken(parts, speech):
    parts.begin(STREAM, EPISODE, None, UNAVAILABLE)

    part = parts.add(STREAM, "Uno.")

    assert part.audio_url is None
    assert speech.synthesized == []
    assert parts.assemble(STREAM, message_id=402) is None


def test_discarding_a_stream_removes_its_parts(parts, speech, tmp_path):
    parts.begin(STREAM, EPISODE, speech(VOICE), UNAVAILABLE)
    parts.add(STREAM, "Uno.")

    parts.discard(STREAM)

    assert not (tmp_path / "parts" / f"{STREAM}-0.wav").exists()
    with pytest.raises(PartNotFound):
        parts.audio(EPISODE, STREAM, 0, timeout=1)


def test_a_stream_expires_after_its_line_has_ended(parts, speech, clock, tmp_path):
    parts.begin(STREAM, EPISODE, speech(VOICE), UNAVAILABLE)
    parts.add(STREAM, "Uno.")
    parts.assemble(STREAM, message_id=402)

    clock.now += PART_TTL_SECONDS - 1
    assert parts.audio(EPISODE, STREAM, 0, timeout=1).exists()
    clock.now += 2
    parts.begin("next", EPISODE, speech(VOICE), UNAVAILABLE)

    with pytest.raises(PartNotFound):
        parts.audio(EPISODE, STREAM, 0, timeout=1)
    assert not (tmp_path / "parts" / f"{STREAM}-0.wav").exists()


def test_parts_are_spoken_on_one_worker_in_order(tmp_path, clock, speech):
    with ThreadPoolExecutor(max_workers=1) as worker:
        parts = SpokenParts(worker, clock, tmp_path)
        parts.begin(STREAM, EPISODE, speech(VOICE), UNAVAILABLE)
        for number in range(5):
            parts.add(STREAM, f"Frase {number}.")
        parts.assemble(STREAM, message_id=402)

    assert [text for _voice, text, _path in speech.synthesized] == [f"Frase {n}." for n in range(5)]


def test_a_voice_that_fails_while_speaking_is_unavailable_with_the_hosts_message(tmp_path, clock):
    from app.services.tts.base import TTSError, VoiceUnavailable

    class Failing(SynchronousExecutor):
        def submit(self, fn, /, *args, **kwargs) -> Future:
            failed: Future = Future()
            failed.set_exception(TTSError("piper is gone"))
            return failed

    parts = SpokenParts(Failing(), clock, tmp_path)
    parts.begin(STREAM, EPISODE, RecordingTtsBuilder()(VOICE), UNAVAILABLE)
    parts.add(STREAM, "Uno.")

    with pytest.raises(VoiceUnavailable) as raised:
        parts.audio(EPISODE, STREAM, 0, timeout=1)
    assert raised.value.user_message == UNAVAILABLE


def test_closing_stops_the_speaking_worker(tmp_path, clock):
    worker = ThreadPoolExecutor(max_workers=1)
    SpokenParts(worker, clock, tmp_path).close()

    with pytest.raises(RuntimeError):
        worker.submit(print)


def test_a_line_whose_parts_are_not_all_spoken_is_not_joined(tmp_path, clock, speech):
    never: Future = Future()

    class Waiting(SynchronousExecutor):
        def submit(self, fn, /, *args, **kwargs) -> Future:
            return never

    parts = SpokenParts(Waiting(), clock, tmp_path, wait_seconds=0.01)
    parts.begin(STREAM, EPISODE, speech(VOICE), UNAVAILABLE)
    parts.add(STREAM, "Uno.")

    assert parts.assemble(STREAM, message_id=402) is None


def test_parts_are_open_until_closed(tmp_path):
    parts = SpokenParts(SynchronousExecutor(), lambda: 0.0, tmp_path)

    assert parts.is_open
    parts.close()
    assert not parts.is_open
