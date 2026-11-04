"""LineSanitiser: a host line keeps only that host's words (research R4, FR-012).

Conservative by design: it only ever removes text. It strips the speaker's own label, cuts the
line where another participant's label starts a line or sentence, and drops stage directions.
Naming someone without a label ("como dice Marco", "Marco, ¿y tú?") is kept.

`StreamingSanitiser` applies the same rules one sentence at a time, for a line that is streamed
(011 research R13.4). It reads and removes the line's address tag before stage directions are
stripped, and removing a tag is not a trim (R19.7).
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.podcasts.services.line_address import ADDRESS_TAG, LineAddress, LineAddressResult
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
        spoken = self.without_own_label(text)
        kept = _STAGE_DIRECTION.sub("", self.cut_at_other_speaker(spoken)[0])
        if kept == spoken:
            return SanitisedLine(spoken.strip(), was_trimmed=False)
        return SanitisedLine(_tidy(kept), was_trimmed=True)

    def without_own_label(self, text: str) -> str:
        return self._own_label.sub("", text.strip(), count=1)

    def cut_at_other_speaker(self, text: str) -> tuple[str, bool]:
        """The text before another participant's label, and whether there was one."""
        match = self._other_label.search(text)
        return (text[: match.start()], True) if match else (text, False)


@dataclass(frozen=True, slots=True)
class SentenceVerdict:
    text: str
    """What is kept of the sentence; empty when nothing is."""
    is_cut: bool
    """Another speaker's words began: the rest of the line is dropped."""


class StreamingSanitiser:
    """One line's sentences, sanitised as they arrive, with its address read at the end."""

    def __init__(self, sanitiser: LineSanitiser, address: LineAddress) -> None:
        self._sanitiser = sanitiser
        self._address = address
        self._raw: list[str] = []
        self._was_trimmed = False

    @property
    def was_trimmed(self) -> bool:
        return self._was_trimmed

    def clean_sentence(self, sentence: str) -> SentenceVerdict:
        spoken = sentence.strip()
        if not self._raw:
            spoken = self._sanitiser.without_own_label(spoken)
        self._raw.append(sentence.strip())
        kept, is_cut = self._sanitiser.cut_at_other_speaker(ADDRESS_TAG.sub("", spoken))
        stripped = _STAGE_DIRECTION.sub("", kept)
        self._was_trimmed = self._was_trimmed or is_cut or stripped != kept
        return SentenceVerdict(_tidy(stripped), is_cut)

    def address(self) -> LineAddressResult:
        """Who the whole line is for, read from its raw text once the line has ended."""
        return self._address.read(" ".join(self._raw))


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
