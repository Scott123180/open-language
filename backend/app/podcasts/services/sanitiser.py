"""LineSanitiser: a host line keeps only that host's words (research R4, FR-012).

Conservative by design: it only ever removes text. It strips the speaker's own label, cuts the
line where another participant's label starts a line or sentence, and drops stage directions.
Naming someone without a label ("como dice Marco", "Marco, ¿y tú?") is kept.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.practice_languages import guest_labels_for

ROLE_WORDS = ("Guest", "Learner", "User", "You")
_SPACES = re.compile(r"[ \t]{2,}")
_SPACE_BEFORE_PUNCTUATION = re.compile(r"[ \t]+([.,;:!?])")
_STAGE_DIRECTION = re.compile(r"\([^)]*\)|\*[^*\n]+\*|\[[^\]\n]*\]")
_SENTENCE_START = r"(?:^|(?<=[.!?…])[ \t]+|\n)"


@dataclass(frozen=True, slots=True)
class SanitisedLine:
    text: str
    was_trimmed: bool


class LineSanitiser:
    def __init__(self, own_name: str, other_labels: Iterable[str]) -> None:
        self._own_label = _label_pattern((own_name,), anchored=True)
        self._other_label = _label_pattern(tuple(other_labels), anchored=False)

    @classmethod
    def for_speaker(
        cls, own_name: str, other_hosts: Iterable[str], learner_name: str | None, language: str
    ) -> "LineSanitiser":
        learner = (learner_name,) if learner_name else ()
        others = (*other_hosts, *learner, *ROLE_WORDS, *guest_labels_for(language))
        return cls(own_name, others)

    def clean(self, text: str) -> SanitisedLine:
        spoken = self._own_label.sub("", text.strip(), count=1)
        kept = _STAGE_DIRECTION.sub("", self._cut_at_other_speaker(spoken))
        if kept == spoken:
            return SanitisedLine(spoken.strip(), was_trimmed=False)
        return SanitisedLine(_tidy(kept), was_trimmed=True)

    def _cut_at_other_speaker(self, text: str) -> str:
        match = self._other_label.search(text)
        return text[: match.start()] if match else text


def _label_pattern(names: tuple[str, ...], anchored: bool) -> re.Pattern[str]:
    """`Name:`, `**Name:**`, `**Name**:` or `[Name]`, at the start or at a sentence start."""
    alternatives = "|".join(re.escape(name) for name in names)
    colon_label = rf"[*_]{{0,2}}\s*(?:{alternatives})\s*[*_]{{0,2}}\s*:[*_]{{0,2}}"
    bracket_label = rf"\[\s*(?:{alternatives})\s*\]:?"
    start = r"^\s*" if anchored else _SENTENCE_START + r"\s*"
    return re.compile(rf"{start}(?:{colon_label}|{bracket_label})\s*", re.IGNORECASE)


def _tidy(text: str) -> str:
    single_spaced = _SPACES.sub(" ", text)
    return _SPACE_BEFORE_PUNCTUATION.sub(r"\1", single_spaced).strip()
