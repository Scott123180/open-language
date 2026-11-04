"""Finding people's names in a line, the same way everywhere in the podcast module."""

import re
import unicodedata
from collections.abc import Iterable


def fold(text: str) -> str:
    """Case- and accent-insensitive form, so "lucia" names Lucía."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def first_mention(text: str, name: str) -> int | None:
    """Where `name` first appears in `text` as a whole word, folded; None if it does not."""
    match = re.search(rf"\b{re.escape(fold(name))}\b", fold(text))
    return match.start() if match else None


def last_mention(text: str, names: Iterable[str]) -> int | None:
    """Where any of `names` last appears in `text` as a whole word, folded."""
    folded = fold(text)
    ends = [
        match.start()
        for name in names
        for match in re.finditer(rf"\b{re.escape(fold(name))}\b", folded)
    ]
    return max(ends) if ends else None
