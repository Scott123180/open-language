"""What a series episode knows of its series, frozen when it starts (010 research R5).

The standing prompt and the cues of a series episode are rendered from its snapshot only, never
from live memory, so resuming an episode gives the model exactly what it had when it began.
These values live apart from the series service so the prompts never depend on it.
"""

import json
from dataclasses import dataclass

from app.podcasts.services.casting import Cast


@dataclass(frozen=True, slots=True)
class SeriesSnapshot:
    episode_number: int
    topics_covered: tuple[str, ...] = ()
    """Newest first, in the conversation's language."""
    about_learner: tuple[str, ...] = ()
    """Newest first, in the conversation's language."""
    new_host_slots: tuple[str, ...] = ()
    """The slots whose host joins the series in this episode (a recast)."""
    guest_slot: str | None = None
    """011: the slot a guest sits in for this episode only; None in 010 snapshots."""

    def to_json(self) -> str:
        """010's JSON byte for byte, plus the 011 keys only when they are set."""
        stored = {
            "episode_number": self.episode_number,
            "topics_covered": list(self.topics_covered),
            "about_learner": list(self.about_learner),
            "new_host_slots": list(self.new_host_slots),
        }
        if self.guest_slot is not None:
            stored["guest_slot"] = self.guest_slot
        return json.dumps(stored, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "SeriesSnapshot":
        stored = json.loads(raw)
        return cls(
            episode_number=stored["episode_number"],
            topics_covered=tuple(stored["topics_covered"]),
            about_learner=tuple(stored["about_learner"]),
            new_host_slots=tuple(stored["new_host_slots"]),
            guest_slot=stored.get("guest_slot"),
        )


@dataclass(frozen=True, slots=True)
class SeriesBrief:
    """The snapshot, with its new hosts named from the episode's cast. None for a one-off."""

    snapshot: SeriesSnapshot
    new_host_slots: tuple[str, ...]
    new_host_names: tuple[str, ...]
    guest_name: str | None = None
    """011: today's guest, named from the cast."""

    @classmethod
    def of(cls, snapshot: SeriesSnapshot, cast: Cast) -> "SeriesBrief":
        """A new host who does not take part in this episode (One host) is not named."""
        present = {host.slot: host.name for host in cast.hosts}
        slots = tuple(slot for slot in snapshot.new_host_slots if slot in present)
        guest = present.get(snapshot.guest_slot) if snapshot.guest_slot else None
        return cls(snapshot, slots, tuple(present[slot] for slot in slots), guest)

    @property
    def guest_slot(self) -> str | None:
        return self.snapshot.guest_slot if self.guest_name else None

    @property
    def episode_number(self) -> int:
        return self.snapshot.episode_number

    def is_new_host(self, slot: str) -> bool:
        return slot in self.new_host_slots
