"""Find words of other languages in a practice-language text, for the adherence benchmarks (R8).

A token is foreign when it is common in another language (Zipf >= 3.0) and at least 1.5 Zipf more
frequent there than in the target. The margin replaces 006's first sketch ("rare in the target,
Zipf < 2.0"): wordfreq's German list carries English loans at high frequency ("the" is 5.6), so
that rule missed the very words the benchmark is about. At a 1.5 margin, every flagged word in
the top 5,000 German tokens is an English, Spanish or French function word.

The other languages are English plus every other catalogued practice language wordfreq covers.
Capitalised tokens after the first in a sentence are skipped: German capitalises every noun, and
in every language proper nouns (Berlin, Maria) are not foreign words.
"""

import re

from wordfreq import available_languages, zipf_frequency

from app.practice_languages import NATIVE_LANGUAGE_NAMES, PRACTICE_LANGUAGES
from tests.integration.practice_languages.evaluation_set import (
    EvaluationSetError,
    evaluation_set,
)

MIN_OTHER_ZIPF = 3.0
MIN_ZIPF_MARGIN = 1.5
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[^\W\d_]+")


def foreign_words(text: str, target: str, others: tuple[str, ...]) -> list[str]:
    """The words of `others` in a `target`-language text, lowercased, in order."""
    allowed = loanwords(target)
    return [
        word
        for sentence in _SENTENCE_END.split(text)
        for word in _checked_words(sentence, allowed)
        if _is_foreign(word, target, others)
    ]


def other_languages(target: str) -> tuple[str, ...]:
    """English, then every other catalogued practice language wordfreq covers."""
    covered = set(available_languages())
    practice = (code for code in PRACTICE_LANGUAGES if code != target and code in covered)
    return (*NATIVE_LANGUAGE_NAMES, *practice)


def loanwords(target: str) -> frozenset[str]:
    """The target's standard words that are common elsewhere too; empty without an evaluation set."""
    try:
        return evaluation_set(target).loanwords
    except EvaluationSetError:
        return frozenset()


def _checked_words(sentence: str, allowed: frozenset[str]) -> list[str]:
    tokens = _WORD.findall(sentence)
    checked = [token for index, token in enumerate(tokens) if index == 0 or token.islower()]
    return [token.lower() for token in checked if token.lower() not in allowed]


def _is_foreign(word: str, target: str, others: tuple[str, ...]) -> bool:
    other = max(zipf_frequency(word, language) for language in others)
    return other >= MIN_OTHER_ZIPF and other - zipf_frequency(word, target) >= MIN_ZIPF_MARGIN
