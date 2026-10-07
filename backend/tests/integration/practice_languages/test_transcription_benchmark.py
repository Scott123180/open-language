"""Transcription benchmark for any practice language, against the real Whisper model (R8).

006's SC-003, made language-independent by 008: each dictation sentence of the language's
evaluation set is spoken by **every** voice of the language, converted to 16 kHz mono, and
transcribed with the configured Whisper model and the language as a hint. Deselected by default;
`kit.sh bench <code> --transcription` runs it, or by hand from `backend/`, voices installed:

    OPEN_LANGUAGE_BENCH_LANGUAGE=de backend/.venv/bin/pytest -m benchmark -s \
        tests/integration/practice_languages/test_transcription_benchmark.py

One table per voice is written before the assertion runs.
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.config import get_settings
from app.services.stt.whisper import WhisperSTTProvider
from app.services.tts.piper import PiperTTSProvider
from app.services.tts.voices import voices_for
from tests.integration.practice_languages.bench_environment import (
    BenchmarkResult,
    bench_languages,
    bench_output_dir,
    record_benchmark,
)
from tests.integration.practice_languages.evaluation_set import evaluation_set

pytestmark = pytest.mark.benchmark

SAMPLE_RATE = 16000
MAX_WORD_ERROR_RATE = 0.20
MIN_PASSING = 18
_WORD = re.compile(r"[^\W_]+")
VOICES = [(code, voice.key) for code in bench_languages() for voice in voices_for(code)]


@dataclass(frozen=True, slots=True)
class Dictation:
    sentence: str
    transcript: str
    special_letters: str
    """Letters a transcript must keep; empty means no such check."""

    @property
    def word_error_rate(self) -> float:
        expected, heard = _words(self.sentence), _words(self.transcript)
        return _edit_distance(expected, heard) / len(expected)

    @property
    def keeps_special_letters(self) -> bool:
        heard = set(_words(self.transcript))
        special = set(self.special_letters)
        return all(word in heard for word in _words(self.sentence) if special & set(word))

    @property
    def passes(self) -> bool:
        return self.keeps_special_letters and self.word_error_rate <= MAX_WORD_ERROR_RATE


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _edit_distance(expected: list[str], heard: list[str]) -> int:
    previous = list(range(len(heard) + 1))
    for index, word in enumerate(expected, start=1):
        current = [index]
        for position, candidate in enumerate(heard, start=1):
            substitution = previous[position - 1] + (word != candidate)
            current.append(min(previous[position] + 1, current[-1] + 1, substitution))
        previous = current
    return previous[-1]


def _speak(voice: str, sentence: str, index: int, directory: Path) -> Path:
    spoken = directory / f"{index}-piper.wav"
    PiperTTSProvider(voice_name=voice, voice_dir=get_settings().voice_dir).synthesize(
        sentence, spoken
    )
    resampled = directory / f"{index}-16k.wav"
    resample = f"-loglevel error -y -i {spoken} -ar {SAMPLE_RATE} -ac 1 {resampled}"
    subprocess.run(["ffmpeg", *resample.split()], check=True)
    return resampled


def _table(dictations: list[Dictation]) -> str:
    rows = [
        f"| {index} | {d.sentence} | {d.transcript} | {d.word_error_rate:.0%} | {d.passes} |"
        for index, d in enumerate(dictations, start=1)
    ]
    return (
        "| # | Sentence | Transcript | WER | Pass |\n|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n"
    )


def _record(code: str, voice: str, dictations: list[Dictation]) -> BenchmarkResult:
    passing = sum(d.passes for d in dictations)
    model = get_settings().whisper_model
    threshold = f"≥ {MIN_PASSING}/{len(dictations)}"
    result = BenchmarkResult("transcription", code, voice, model, passing, len(dictations), threshold, passing >= MIN_PASSING)  # fmt: skip
    verdict = "met" if result.met else "missed"
    section = (
        f"## Transcription: {voice} (006 SC-003)\n\nWhisper model: {model}.\n\n{_table(dictations)}\n"
        f"Sentences passing: {passing}/{len(dictations)} against {threshold}: {verdict}.\n"
    )
    record_benchmark(bench_output_dir(code), result, section)
    return result


@pytest.mark.parametrize(("code", "voice"), VOICES)
def test_dictation_is_transcribed_with_its_special_letters(code, voice, tmp_path, capsys) -> None:
    settings = get_settings()
    stt = WhisperSTTProvider(model_size=settings.whisper_model, device=settings.whisper_device)
    evaluation = evaluation_set(code)
    dictations = [
        Dictation(
            sentence,
            stt.transcribe(_speak(voice, sentence, i, tmp_path), code).text,
            evaluation.special_letters,
        )
        for i, sentence in enumerate(evaluation.dictation)
    ]
    result = _record(code, voice, dictations)

    with capsys.disabled():
        print(f"\n{code} {voice}: {result.passed}/{result.total} sentences passing")  # noqa: T201

    assert result.met
