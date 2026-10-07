"""Fakes for the kit's boundaries: they substitute for the real collaborators (LSP)."""

from datetime import UTC, datetime, timedelta

from language_kit.bench import BenchProbe
from language_kit.clock import Clock
from language_kit.errors import KitExternalError
from language_kit.verify import CommandRunner, CompletedRun
from language_kit.voices import (
    VoiceCandidate,
    VoiceCatalogue,
    VoiceDownload,
    VoiceDownloader,
    VoiceFile,
)

COUNTRIES = {"it_IT": "Italy", "de_DE": "Germany", "es_ES": "Spain", "es_AR": "Argentina"}
LANGUAGE_NAMES = {"it": "Italian", "de": "German", "es": "Spanish", "fr": "French"}
MEGABYTE = 1_000_000


def candidate(key: str, quality: str | None = None, megabytes: int = 60) -> VoiceCandidate:
    region, name, tier = key.split("-")
    code = region.split("_")[0]
    folder = f"{code}/{region}/{name}/{tier}"
    files = (
        VoiceFile(f"{folder}/{key}.onnx", f"md5-{key}-onnx", megabytes * MEGABYTE),
        VoiceFile(f"{folder}/{key}.onnx.json", f"md5-{key}-json", 5_000),
    )
    size = sum(file.size_bytes for file in files)
    country = COUNTRIES.get(region, region)
    language_name = LANGUAGE_NAMES.get(code, code)
    return VoiceCandidate(key, name, region, country, quality or tier, size, files, language_name)


class FakeVoiceCatalogue(VoiceCatalogue):
    def __init__(self, voices: list[VoiceCandidate]) -> None:
        self._voices = {voice.key: voice for voice in voices}
        self.calls = 0

    def candidates(self, code: str) -> tuple[VoiceCandidate, ...]:
        self.calls += 1
        return tuple(v for v in self._voices.values() if v.region.split("_")[0] == code)

    def voice(self, key: str) -> VoiceCandidate | None:
        self.calls += 1
        return self._voices.get(key)


class FixedClock(Clock):
    def __init__(self, start: datetime = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


class FakeVoiceDownloader(VoiceDownloader):
    """Writes placeholder voice files; can be told to fail, and to check something first."""

    def __init__(self, voice_dir, failing: set[str] | None = None, before=None) -> None:
        self._voice_dir = voice_dir
        self._failing = failing or set()
        self._before = before
        self.ensured: list[str] = []

    def ensure(self, voice: VoiceCandidate) -> VoiceDownload:
        if self._before is not None:
            self._before(voice)
        self.ensured.append(voice.key)
        if voice.key in self._failing:
            raise KitExternalError(f"{voice.key}: checksum mismatch")
        for suffix in (".onnx", ".onnx.json"):
            (self._voice_dir / f"{voice.key}{suffix}").write_bytes(b"voice")
        return VoiceDownload(voice.key, downloaded=True, seconds=1.5)


class FakeCommandRunner(CommandRunner):
    """Returns scripted (exit code, output) per suite log name; passing output otherwise."""

    def __init__(self, scripted: dict[str, tuple[int, str]] | None = None) -> None:
        self._scripted = scripted or {}
        self.calls: list[tuple[str, list[str], object, object]] = []
        self.environments: list[dict[str, str]] = []

    def run(self, argv, cwd, log, environment=None) -> CompletedRun:
        name = log.stem
        self.calls.append((name, list(argv), cwd, log))
        self.environments.append(dict(environment or {}))
        exit_code, output = self._scripted.get(name, (0, "All checks passed!"))
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(output, encoding="utf-8")
        return CompletedRun(exit_code, output)


class FakeBenchProbe(BenchProbe):
    def __init__(self, ollama_problem: str | None = None) -> None:
        self._ollama_problem = ollama_problem

    def ollama_problem(self) -> str | None:
        return self._ollama_problem
