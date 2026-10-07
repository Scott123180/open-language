"""Voices offered for a language and fetching them: interfaces first, implementations below.

The catalogue is Piper's `voices.json`, from the host `run.sh` downloads voices from. It has no
gender field, so a pack asserts each voice's gender (research R6).
"""

import hashlib
import json
import shutil
import time
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from language_kit.clock import Clock, SystemClock
from language_kit.errors import KitExternalError

VOICE_FILES_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
CATALOGUE_URL = f"{VOICE_FILES_URL}voices.json"
CATALOGUE_CACHE = Path.home() / ".cache" / "open-language" / "piper-voices.json"
CATALOGUE_TTL = timedelta(hours=24)
VOICE_SUFFIXES = (".onnx", ".onnx.json")
SINGLE_SPEAKER = 1
PARTIAL_SUFFIX = ".part"
READ_CHUNK_BYTES = 1 << 20


@dataclass(frozen=True, slots=True)
class VoiceFile:
    relative_path: str
    """Path under the voice repository, e.g. `it/it_IT/paola/medium/it_IT-paola-medium.onnx`."""
    md5: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class VoiceCandidate:
    """A single-speaker catalogue voice. The catalogue has no gender: the pack asserts it."""

    key: str
    name: str
    region: str
    """The locale, e.g. `it_IT`."""
    country: str
    """The country in English, e.g. `Italy`."""
    quality: str
    size_bytes: int
    files: tuple[VoiceFile, ...]
    language_name: str = ""
    """The language's English name, e.g. `Italian`."""


class VoiceCatalogue(ABC):
    @abstractmethod
    def candidates(self, code: str) -> tuple[VoiceCandidate, ...]:
        """The single-speaker voices of a language."""

    @abstractmethod
    def voice(self, key: str) -> VoiceCandidate | None:
        """One single-speaker voice by key, or None when the catalogue has no such voice."""


@dataclass(frozen=True, slots=True)
class VoiceDownload:
    key: str
    downloaded: bool
    """False when every file was already present with the right checksum."""
    seconds: float


class VoiceDownloader(ABC):
    @abstractmethod
    def ensure(self, voice: VoiceCandidate) -> VoiceDownload:
        """Make sure the voice's files are in the voice directory, checksums verified."""


# ── Implementations ──────────────────────────────────────────────────────────────────


def fetch_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url) as response:  # noqa: S310 - fixed https catalogue URL
        data: bytes = response.read()
    return data


def download_file(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url) as response, destination.open("wb") as file:  # noqa: S310
        shutil.copyfileobj(response, file, READ_CHUNK_BYTES)


class PiperVoiceCatalogue(VoiceCatalogue):
    """Piper's catalogue, cached on disk for a day; offers only single-speaker voices."""

    def __init__(
        self,
        fetch: Callable[[str], bytes] = fetch_bytes,
        cache_path: Path = CATALOGUE_CACHE,
        clock: Clock | None = None,
    ) -> None:
        self._fetch = fetch
        self._cache_path = cache_path
        self._clock = clock or SystemClock()
        self._voices: dict[str, Any] | None = None

    def candidates(self, code: str) -> tuple[VoiceCandidate, ...]:
        entries = self._entries().values()
        return tuple(
            _candidate(e)
            for e in entries
            if _is_single_speaker(e) and e["language"]["family"] == code
        )

    def voice(self, key: str) -> VoiceCandidate | None:
        entry = self._entries().get(key)
        return _candidate(entry) if entry is not None and _is_single_speaker(entry) else None

    def _entries(self) -> dict[str, Any]:
        if self._voices is None:
            self._voices = self._cached() or self._download()
        return self._voices

    def _cached(self) -> dict[str, Any] | None:
        try:
            cache = json.loads(self._cache_path.read_text(encoding="utf-8"))
            fetched_at = datetime.fromisoformat(cache["fetched_at"])
        except (OSError, ValueError, KeyError, TypeError):
            return None
        fresh = self._clock.now() - fetched_at < CATALOGUE_TTL
        return dict(cache["voices"]) if fresh else None

    def _download(self) -> dict[str, Any]:
        try:
            voices = json.loads(self._fetch(CATALOGUE_URL))
        except (OSError, ValueError) as error:
            raise KitExternalError(
                f"voice discovery needs the network ({error}): {CATALOGUE_URL}"
            ) from error
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache = {"fetched_at": self._clock.now().isoformat(), "voices": voices}
        self._cache_path.write_text(json.dumps(cache), encoding="utf-8")
        return dict(voices)


class HttpVoiceDownloader(VoiceDownloader):
    """Downloads a voice's model and config into the voice directory, MD5-checked."""

    def __init__(
        self,
        voice_dir: Path,
        download: Callable[[str, Path], None] = download_file,
        timer: Callable[[], float] = time.monotonic,
    ) -> None:
        self._voice_dir = voice_dir
        self._download = download
        self._timer = timer

    def ensure(self, voice: VoiceCandidate) -> VoiceDownload:
        started = self._timer()
        self._voice_dir.mkdir(parents=True, exist_ok=True)
        fetched = [self._fetch(file) for file in voice.files if not self._is_present(file)]
        return VoiceDownload(voice.key, downloaded=bool(fetched), seconds=self._timer() - started)

    def _fetch(self, file: VoiceFile) -> Path:
        target = self._target(file)
        partial = target.with_name(target.name + PARTIAL_SUFFIX)
        try:
            self._download(VOICE_FILES_URL + file.relative_path, partial)
        except OSError as error:
            partial.unlink(missing_ok=True)
            raise KitExternalError(f"downloading {target.name} failed: {error}") from error
        if _md5(partial) != file.md5:
            partial.unlink()
            raise KitExternalError(
                f"{target.name}: checksum mismatch; the download was deleted, try again"
            )
        return partial.replace(target)

    def _is_present(self, file: VoiceFile) -> bool:
        target = self._target(file)
        return target.is_file() and _md5(target) == file.md5

    def _target(self, file: VoiceFile) -> Path:
        return self._voice_dir / Path(file.relative_path).name


def _is_single_speaker(entry: dict[str, Any]) -> bool:
    return bool(entry.get("num_speakers") == SINGLE_SPEAKER)


def _candidate(entry: dict[str, Any]) -> VoiceCandidate:
    files = tuple(
        VoiceFile(path, details["md5_digest"], details["size_bytes"])
        for path, details in entry["files"].items()
        if path.endswith(VOICE_SUFFIXES)
    )
    language = entry["language"]
    return VoiceCandidate(
        key=entry["key"],
        name=entry["name"],
        region=language["code"],
        country=language["country_english"],
        quality=entry["quality"],
        size_bytes=sum(file.size_bytes for file in files),
        files=files,
        language_name=language["name_english"],
    )


def _md5(path: Path) -> str:
    digest = hashlib.md5()  # noqa: S324 - Piper publishes MD5 checksums
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(READ_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()
