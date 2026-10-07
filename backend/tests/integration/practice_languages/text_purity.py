"""Find English or Spanish words in German text, for the SC-002 benchmark (research R8).

A token is foreign when it is common in English or Spanish (Zipf >= 3.0) and at least 1.5 Zipf
more frequent there than in German. The margin replaces R8's first sketch ("rare in German,
Zipf < 2.0"): wordfreq's German list carries English loans at high frequency ("the" is 5.6), so
that rule missed the very words SC-002 is about. At a 1.5 margin, every flagged word in the top
5,000 German tokens is an English, Spanish or French function word.

Capitalised tokens after the first in a sentence are skipped: German capitalises every noun, and
proper nouns (Berlin, Maria) are not foreign words.
"""

import re

from wordfreq import zipf_frequency

from tests.integration.practice_languages.evaluation_set import evaluation_set

GERMAN = "de"
OTHER_LANGUAGES = ("en", "es")
MIN_OTHER_ZIPF = 3.0
MIN_ZIPF_MARGIN = 1.5
LOANWORD_ALLOWLIST = evaluation_set(GERMAN).loanwords
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[^\W\d_]+")


def foreign_words(text: str) -> list[str]:
    """The English or Spanish words in a German text, lowercased, in order."""
    return [
        word
        for sentence in _SENTENCE_END.split(text)
        for word in _checked_words(sentence)
        if _is_foreign(word)
    ]


def _checked_words(sentence: str) -> list[str]:
    tokens = _WORD.findall(sentence)
    checked = [token for index, token in enumerate(tokens) if index == 0 or token.islower()]
    return [token.lower() for token in checked if token.lower() not in LOANWORD_ALLOWLIST]


def _is_foreign(word: str) -> bool:
    other = max(zipf_frequency(word, language) for language in OTHER_LANGUAGES)
    return other >= MIN_OTHER_ZIPF and other - zipf_frequency(word, GERMAN) >= MIN_ZIPF_MARGIN
