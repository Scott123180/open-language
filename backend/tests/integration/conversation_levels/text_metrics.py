"""Deterministic, language-neutral text measures for the level benchmark (research R9).

Sentences end at `.`, `!`, `?` or `…`; Spanish inverted openers (`¿`, `¡`) start a sentence but
never end one. Words are runs of Unicode letters, so digits and punctuation are not counted.
"""

import re
from collections.abc import Iterable
from statistics import fmean

_SENTENCE_BREAK = re.compile(r"(?<=[.!?…])\s+|(?<=[.!?…])(?=[¿¡])")
_WORD = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")

# Common English function words that are not also Spanish words (so "no", "me", "a" are absent).
NATIVE_LANGUAGE_MARKERS = frozenset(
    {
        "the", "and", "is", "are", "was", "were", "you", "your", "what", "with", "this", "that",
        "of", "to", "it", "for", "have", "has", "do", "does", "please", "hello", "yes", "thank",
        "thanks", "would", "can", "will", "how", "where", "there", "here", "my", "we", "they",
        "be", "not", "but", "or", "an", "in", "on", "at", "from", "about", "like", "just",
    }
)  # fmt: skip


def split_sentences(text: str) -> list[str]:
    """The sentences of `text`, ignoring pieces that hold no word."""
    pieces = (piece.strip() for piece in _SENTENCE_BREAK.split(text.strip()))
    return [piece for piece in pieces if _WORD.search(piece)]


def words(text: str) -> list[str]:
    return _WORD.findall(text)


def words_per_sentence(text: str) -> list[int]:
    return [len(words(sentence)) for sentence in split_sentences(text)]


def meets_length_limits(text: str, max_sentences: int, max_words_per_sentence: int) -> bool:
    """Whether a reply keeps to a level's reply length and sentence length."""
    counts = words_per_sentence(text)
    return len(counts) <= max_sentences and all(count <= max_words_per_sentence for count in counts)


def mean_words_per_sentence(texts: Iterable[str]) -> float:
    counts = [count for text in texts for count in words_per_sentence(text)]
    return fmean(counts) if counts else 0.0


def share_outside(texts: Iterable[str], common_words: frozenset[str]) -> float:
    """The share of words, lower-cased, that are not in `common_words`."""
    all_words = [word.lower() for text in texts for word in words(text)]
    if not all_words:
        return 0.0
    return sum(word not in common_words for word in all_words) / len(all_words)


def native_language_words(text: str) -> list[str]:
    """English function words found in `text` (SC-004)."""
    return [word for word in words(text) if word.lower() in NATIVE_LANGUAGE_MARKERS]
