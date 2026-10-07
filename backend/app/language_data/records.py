"""The typed records one practice-language data file loads into (contracts/data-files.md)."""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VoiceRecord:
    key: str
    display_name: str
    gender: str
    locale: str
    quality: str
    speaking_rate: str


@dataclass(frozen=True, slots=True)
class PodcastRecord:
    host_names: Mapping[str, tuple[str, ...]]
    """Podcast host names keyed by the gender of the host's voice."""
    guest_labels: tuple[str, ...]
    sample_line: str
    """What a host says in a voice sample. Holds exactly one `{name}`."""


@dataclass(frozen=True, slots=True)
class LanguageRecord:
    code: str
    name: str
    order: int
    """Display order among the practice languages."""
    default_voice: str
    voices: tuple[VoiceRecord, ...]
    podcast: PodcastRecord
