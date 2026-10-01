"""Language data a podcast host needs: names, the words for a guest, and a voice sample."""

from app.practice_languages.catalog import PRACTICE_LANGUAGES, PracticeLanguage
from app.practice_languages.naming import UnknownLanguage


def _language(code: str) -> PracticeLanguage:
    if code not in PRACTICE_LANGUAGES:
        raise UnknownLanguage(code)
    return PRACTICE_LANGUAGES[code]


def host_names_for(code: str, gender: str) -> tuple[str, ...]:
    """Names that suit the language for a host whose voice has `gender`."""
    return _language(code).host_names.get(gender, ())


def guest_labels_for(code: str) -> tuple[str, ...]:
    return _language(code).guest_labels


def voice_sample_line(code: str, name: str) -> str:
    return _language(code).sample_line.format(name=name)
