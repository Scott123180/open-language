"""SentenceSplitter: a streamed host line, cut into sentences as they complete (research R13.3).

A sentence ends at `.`, `!`, `?` or `…`, with any closing quotes or brackets, when whitespace and
the start of a new sentence follow: an upper-case letter, a digit, `¿`, `¡` or an opening quote.
A newline always ends one. A sentence shorter than `MIN_SENTENCE_CHARACTERS` joins the next, so
"Sr." never stands alone. Only punctuation is read: no abbreviation lists, no per-language data.
"""

import re

from app.podcasts.catalog import MIN_SENTENCE_CHARACTERS

_END_OF_SENTENCE = re.compile(r"[.!?…]+[\"'”’»)\]]*[ \t]+(?=\S)|\n")
_SENTENCE_OPENERS = "¿¡\"'“‘«"


class SentenceSplitter:
    def __init__(self) -> None:
        self._buffer = ""
        """Text not yet cut into a sentence."""
        self._short = ""
        """Cut sentences too short to stand alone, waiting to join the next."""

    def feed(self, token: str) -> list[str]:
        """The sentences `token` completes, in order."""
        self._buffer += token
        sentences = []
        while (cut := self._next_cut()) is not None:
            self._short += self._buffer[:cut]
            self._buffer = self._buffer[cut:]
            if len(self._short.strip()) >= MIN_SENTENCE_CHARACTERS:
                sentences.append(self._short.strip())
                self._short = ""
        return sentences

    def flush(self) -> str:
        """Everything not yet given as a sentence, or "" when there is nothing."""
        rest = (self._short + self._buffer).strip()
        self._short = self._buffer = ""
        return rest

    def _next_cut(self) -> int | None:
        for match in _END_OF_SENTENCE.finditer(self._buffer):
            if match.group() == "\n" or _starts_sentence(self._buffer[match.end()]):
                return match.end()
        return None


def _starts_sentence(char: str) -> bool:
    return char.isupper() or char.isdigit() or char in _SENTENCE_OPENERS
