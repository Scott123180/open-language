"""T054: the Piper voice catalogue, fetched once a day and filtered to single-speaker voices (R6)."""

import json
from datetime import timedelta
from pathlib import Path

import pytest

from language_kit.errors import KitExternalError
from language_kit.voices import CATALOGUE_TTL, CATALOGUE_URL, PiperVoiceCatalogue, fetch_bytes
from tests.unit.language_kit.fakes import FixedClock

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "language_kit" / "voices.json"


class CountingFetch:
    def __init__(self, failing: bool = False) -> None:
        self.urls: list[str] = []
        self._failing = failing

    def __call__(self, url: str) -> bytes:
        self.urls.append(url)
        if self._failing:
            raise OSError("network is unreachable")
        return FIXTURE.read_bytes()


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


def _catalogue(tmp_path: Path, clock: FixedClock, fetch=None) -> PiperVoiceCatalogue:
    return PiperVoiceCatalogue(
        fetch or CountingFetch(), tmp_path / "cache" / "piper-voices.json", clock
    )


def test_the_catalogue_is_fetched_from_the_piper_voices_repository(tmp_path, clock):
    fetch = CountingFetch()

    _catalogue(tmp_path, clock, fetch).candidates("it")

    assert fetch.urls == [CATALOGUE_URL]
    assert CATALOGUE_URL == "https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json"


def test_candidates_are_the_single_speaker_voices_of_the_language(tmp_path, clock):
    keys = [voice.key for voice in _catalogue(tmp_path, clock).candidates("de")]

    assert keys == ["de_DE-thorsten-medium"]


def test_a_candidate_carries_region_country_quality_size_and_checksums(tmp_path, clock):
    paola, riccardo = _catalogue(tmp_path, clock).candidates("it")

    assert (paola.key, paola.name, paola.region, paola.country, paola.quality) == (
        "it_IT-paola-medium",
        "paola",
        "it_IT",
        "Italy",
        "medium",
    )
    assert paola.size_bytes == 63_201_294 + 5000
    assert [file.md5 for file in paola.files] == ["p1a", "p1b"]
    assert paola.language_name == "Italian"
    assert riccardo.quality == "x_low"


def test_one_voice_is_found_by_key_unless_it_has_many_speakers(tmp_path, clock):
    catalogue = _catalogue(tmp_path, clock)

    assert catalogue.voice("it_IT-paola-medium").country == "Italy"
    assert catalogue.voice("de_DE-mls-medium") is None
    assert catalogue.voice("xx_XX-none-low") is None


def test_the_catalogue_is_cached_for_a_day(tmp_path, clock):
    fetch = CountingFetch()
    _catalogue(tmp_path, clock, fetch).candidates("it")
    clock.advance(CATALOGUE_TTL.total_seconds() - 60)

    _catalogue(tmp_path, clock, fetch).candidates("it")

    assert len(fetch.urls) == 1


def test_an_expired_cache_is_fetched_again(tmp_path, clock):
    fetch = CountingFetch()
    _catalogue(tmp_path, clock, fetch).candidates("it")
    clock.advance((CATALOGUE_TTL + timedelta(minutes=1)).total_seconds())

    _catalogue(tmp_path, clock, fetch).candidates("it")

    assert len(fetch.urls) == 2


def test_a_corrupt_cache_is_fetched_again(tmp_path, clock):
    cache = tmp_path / "cache" / "piper-voices.json"
    cache.parent.mkdir()
    cache.write_text("not json", encoding="utf-8")
    fetch = CountingFetch()

    _catalogue(tmp_path, clock, fetch).candidates("it")

    assert len(fetch.urls) == 1 and json.loads(cache.read_text(encoding="utf-8"))["voices"]


def test_a_network_error_says_voice_discovery_needs_the_network(tmp_path, clock):
    with pytest.raises(KitExternalError, match="needs the network"):
        _catalogue(tmp_path, clock, CountingFetch(failing=True)).candidates("it")


def test_fetch_bytes_reads_a_url():
    assert fetch_bytes(FIXTURE.as_uri()) == FIXTURE.read_bytes()
