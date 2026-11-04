"""LineAddress: who a written host line is for (011 research R19.3).

Every configured line ends with a hidden tag, `[@Name]` or `[@all]`. The last valid tag decides;
without one, a line ending in a question is for the last participant it names, and a line naming
the other host is for them. Tags are removed before anything is shown, spoken or remembered. Pure:
names come from the cast, the learner's label and the existing guest labels, never from new
per-language data (FR-027).
"""

import re
from dataclasses import dataclass

from app.podcasts.catalog import ADDRESS_ALL, ADDRESS_TAG_MAX_LENGTH
from app.podcasts.services.casting import Cast
from app.podcasts.services.names import first_mention, fold, last_mention
from app.podcasts.services.turn_policy import LEARNER, ends_with_question
from app.practice_languages import guest_labels_for

ADDRESS_TAG = re.compile(rf"\[@\s*([^\]\n]{{1,{ADDRESS_TAG_MAX_LENGTH}}}?)\s*\]")
_SPACES = re.compile(r"[ \t]{2,}")


@dataclass(frozen=True, slots=True)
class LineAddressResult:
    addressee: str | None
    """learner, lead or second; None for no one in particular."""
    text: str
    """The line with every address tag removed."""
    is_from_tag: bool
    """A valid tag decided, rather than the fallback (SC-012's tag share)."""


class LineAddress:
    def __init__(self, participants: dict[str, tuple[str, ...]], other_host: str | None) -> None:
        """`participants`: each one who may be addressed, with the names that refer to them."""
        self._participants = participants
        self._other_host = other_host

    @classmethod
    def for_episode(
        cls, cast: Cast, learner_label: str, speaker_slot: str, language: str, is_listening: bool
    ) -> "LineAddress":
        participants = {host.slot: (host.name,) for host in cast.hosts if host.slot != speaker_slot}
        if not is_listening:
            participants[LEARNER] = (learner_label, *guest_labels_for(language))
        other = next((slot for slot in participants if slot != LEARNER), None)
        return cls(participants, other)

    def read(self, text: str) -> LineAddressResult:
        tags = ADDRESS_TAG.findall(text)
        untagged = _tidy(ADDRESS_TAG.sub("", text))
        is_valid, tagged = self._tagged(tags[-1]) if tags else (False, None)
        if is_valid:
            return LineAddressResult(tagged, untagged, is_from_tag=True)
        return LineAddressResult(self._fallback(untagged), untagged, is_from_tag=False)

    def _tagged(self, tag: str) -> tuple[bool, str | None]:
        """Whether the tag names a participant or all, and whom."""
        if fold(tag) == ADDRESS_ALL:
            return True, None
        for slot, names in self._participants.items():
            if any(fold(name) == fold(tag) for name in names):
                return True, slot
        return False, None

    def _fallback(self, text: str) -> str | None:
        if ends_with_question(text):
            asked = self._last_named(text)
            if asked is not None:
                return asked
        if self._other_host is None:
            return None
        names = self._participants[self._other_host]
        return self._other_host if first_mention(text, names[0]) is not None else None

    def _last_named(self, text: str) -> str | None:
        positions = {
            slot: position
            for slot, names in self._participants.items()
            if (position := last_mention(text, names)) is not None
        }
        return max(positions, key=positions.get) if positions else None


def _tidy(text: str) -> str:
    return _SPACES.sub(" ", text).strip()
