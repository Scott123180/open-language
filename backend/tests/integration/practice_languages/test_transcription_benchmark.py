"""SC-003 German transcription benchmark against the real Whisper model (research R14).

Each dictation sentence is spoken by the German Piper voice, converted to 16 kHz mono, and
transcribed with the configured Whisper model and a German hint. Deselected by default; run it by
hand from `backend/`, with the German voices installed, and record the printed table:

    backend/.venv/bin/pytest -m benchmark -s \
        tests/integration/practice_languages/test_transcription_benchmark.py
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.config import get_settings
from app.services.stt.whisper import WhisperSTTProvider
from app.services.tts.piper import PiperTTSProvider
from tests.integration.practice_languages.german_evaluation_set import DICTATION_SENTENCES

pytestmark = pytest.mark.benchmark

VOICE = "de_DE-kerstin-low"
LANGUAGE_HINT = "de"
SAMPLE_RATE = 16000
MAX_WORD_ERROR_RATE = 0.20
SC_003_MIN_PASSING = 18
_WORD = re.compile(r"[^\W_]+")
_SPECIAL_LETTERS = re.compile("[äöüß]")


@dataclass(frozen=True, slots=True)
class Dictation:
    sentence: str
    transcript: str

    @property
    def word_error_rate(self) -> float:
        expected, heard = _words(self.sentence), _words(self.transcript)
        return _edit_distance(expected, heard) / len(expected)

    @property
    def keeps_special_letters(self) -> bool:
        heard = set(_words(self.transcript))
        return all(word in heard for word in _words(self.sentence) if _SPECIAL_LETTERS.search(word))

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


def _speak(sentence: str, index: int, directory: Path) -> Path:
    spoken = directory / f"{index}-piper.wav"
    PiperTTSProvider(voice_name=VOICE, voice_dir=get_settings().voice_dir).synthesize(
        sentence, spoken
    )
    resampled = directory / f"{index}-16k.wav"
    resample = f"-loglevel error -y -i {spoken} -ar {SAMPLE_RATE} -ac 1 {resampled}"
    subprocess.run(["ffmpeg", *resample.split()], check=True)
    return resampled


def _print_table(dictations: list[Dictation]) -> None:
    print("\n| # | Sentence | Transcript | WER | Pass |\n|---|---|---|---|---|")  # noqa: T201
    for index, d in enumerate(dictations, start=1):
        row = f"| {index} | {d.sentence} | {d.transcript} | {d.word_error_rate:.0%} | {d.passes} |"
        print(row)  # noqa: T201


def test_german_dictation_meets_sc_003(tmp_path, capsys) -> None:
    settings = get_settings()
    stt = WhisperSTTProvider(model_size=settings.whisper_model, device=settings.whisper_device)
    dictations = [
        Dictation(sentence, stt.transcribe(_speak(sentence, index, tmp_path), LANGUAGE_HINT).text)
        for index, sentence in enumerate(DICTATION_SENTENCES)
    ]
    passing = sum(d.passes for d in dictations)

    with capsys.disabled():
        _print_table(dictations)
        print(f"SC-003 sentences passing: {passing}/{len(dictations)}")  # noqa: T201

    assert passing >= SC_003_MIN_PASSING
