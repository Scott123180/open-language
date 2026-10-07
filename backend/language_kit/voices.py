"""Voices offered for a language and fetching them: interfaces first, implementations below."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


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
