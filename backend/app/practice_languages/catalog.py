"""The languages a learner can practise, built from the files in `app/language_data/languages/`."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.language_data import LanguageRecord, load_language_records


@dataclass(frozen=True, slots=True)
class PracticeLanguage:
    code: str
    name: str
    default_voice: str
    host_names: Mapping[str, tuple[str, ...]]
    """Podcast host names that suit the language, keyed by the gender of the host's voice."""
    guest_labels: tuple[str, ...]
    """The language's own words for a show's guest, cut from host lines like any label."""
    sample_line: str
    """What a host says in a voice sample. Holds exactly one `{name}`."""


def _practice_language(record: LanguageRecord) -> PracticeLanguage:
    return PracticeLanguage(
        code=record.code,
        name=record.name,
        default_voice=record.default_voice,
        host_names=MappingProxyType(dict(record.podcast.host_names)),
        guest_labels=record.podcast.guest_labels,
        sample_line=record.podcast.sample_line,
    )


PRACTICE_LANGUAGES: Mapping[str, PracticeLanguage] = MappingProxyType(
    {record.code: _practice_language(record) for record in load_language_records()}
)
"""Every practice language, in display order."""

DEFAULT_PRACTICE_LANGUAGE = "es"

NATIVE_LANGUAGE_NAMES: Mapping[str, str] = MappingProxyType({"en": "English"})
"""Languages explanations are written in. Not selectable, but prompts need their names."""
