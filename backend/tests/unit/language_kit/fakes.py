"""Fakes for the kit's boundaries: they substitute for the real collaborators (LSP)."""

from datetime import UTC, datetime, timedelta

from language_kit.clock import Clock
from language_kit.voices import VoiceCandidate, VoiceCatalogue, VoiceFile

COUNTRIES = {"it_IT": "Italy", "de_DE": "Germany", "es_ES": "Spain", "es_AR": "Argentina"}
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
    return VoiceCandidate(
        key, name, region, COUNTRIES.get(region, region), quality or tier, size, files
    )


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
