"""How a language is named in prompt text: "German", never its code (research R2)."""

from dataclasses import dataclass

from app.practice_languages.catalog import NATIVE_LANGUAGE_NAMES, PRACTICE_LANGUAGES


class UnknownLanguage(ValueError):  # noqa: N818 — the name is fixed by contracts/api.md §9
    """A language code that is not in the catalogue, such as a corrupt stored value."""

    def __init__(self, code: str) -> None:
        super().__init__(f"Language code {code!r} is not in the language catalogue.")
        self.code = code


def practice_language_name(code: str) -> str:
    if code not in PRACTICE_LANGUAGES:
        raise UnknownLanguage(code)
    return PRACTICE_LANGUAGES[code].name


def language_name(code: str) -> str:
    """The English name of a practice or native language."""
    if code in PRACTICE_LANGUAGES:
        return PRACTICE_LANGUAGES[code].name
    if code in NATIVE_LANGUAGE_NAMES:
        return NATIVE_LANGUAGE_NAMES[code]
    raise UnknownLanguage(code)


@dataclass(frozen=True, slots=True)
class ConversationLanguages:
    """A conversation's languages as prompts need them."""

    target_code: str
    target_name: str
    native_name: str

    @classmethod
    def of(cls, target_code: str, native_code: str) -> "ConversationLanguages":
        return cls(
            target_code=target_code,
            target_name=practice_language_name(target_code),
            native_name=language_name(native_code),
        )
