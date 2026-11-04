"""What a series episode knows of its series, frozen when it starts (010 research R5).

The standing prompt and the cues of a series episode are rendered from its snapshot only, never
from live memory, so resuming an episode gives the model exactly what it had when it began.
These values live apart from the series service so the prompts never depend on it.

011 adds who missed each point (research R11), today's guest and the host they replace. A
snapshot with none of them is written byte for byte as 010 wrote it.
"""

import json
from dataclasses import dataclass

from app.podcasts.services.casting import Cast


@dataclass(frozen=True, slots=True)
class RememberedLine:
    """A remembered point, and the slots of the hosts in this episode who were not there."""

    text: str
    missed_by: tuple[str, ...] = ()


Point = RememberedLine | str


@dataclass(frozen=True, slots=True)
class SeriesSnapshot:
    episode_number: int
    topics_covered: tuple[RememberedLine, ...] = ()
    """Newest first, in the conversation's language. Text is read as an unmarked point."""
    about_learner: tuple[RememberedLine, ...] = ()
    """Newest first, in the conversation's language. Text is read as an unmarked point."""
    new_host_slots: tuple[str, ...] = ()
    """The slots whose host joins the series in this episode (a recast)."""
    guest_slot: str | None = None
    """011: the slot a guest sits in for this episode only; None in 010 snapshots."""
    away_host_name: str | None = None
    """011: the regular host the guest replaces today; None when nobody is away."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "topics_covered", _lines(self.topics_covered))
        object.__setattr__(self, "about_learner", _lines(self.about_learner))

    def to_json(self) -> str:
        """010's JSON byte for byte, plus the 011 keys only when they are set."""
        stored = {
            "episode_number": self.episode_number,
            "topics_covered": [_line_json(line) for line in self.topics_covered],
            "about_learner": [_line_json(line) for line in self.about_learner],
            "new_host_slots": list(self.new_host_slots),
        }
        optional = {"guest_slot": self.guest_slot, "away_host_name": self.away_host_name}
        stored.update({key: value for key, value in optional.items() if value is not None})
        return json.dumps(stored, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "SeriesSnapshot":
        stored = json.loads(raw)
        return cls(
            episode_number=stored["episode_number"],
            topics_covered=tuple(_line_of(point) for point in stored["topics_covered"]),
            about_learner=tuple(_line_of(point) for point in stored["about_learner"]),
            new_host_slots=tuple(stored["new_host_slots"]),
            guest_slot=stored.get("guest_slot"),
            away_host_name=stored.get("away_host_name"),
        )

    @property
    def has_marks(self) -> bool:
        return any(line.missed_by for line in (*self.topics_covered, *self.about_learner))


def _lines(points: tuple[Point, ...]) -> tuple[RememberedLine, ...]:
    return tuple(
        point if isinstance(point, RememberedLine) else RememberedLine(point) for point in points
    )


def _line_json(line: RememberedLine) -> str | dict:
    """An unmarked point stays a plain string, as in 010."""
    if not line.missed_by:
        return line.text
    return {"text": line.text, "missed_by": list(line.missed_by)}


def _line_of(stored: str | dict) -> RememberedLine:
    if isinstance(stored, str):
        return RememberedLine(stored)
    return RememberedLine(stored["text"], tuple(stored["missed_by"]))


@dataclass(frozen=True, slots=True)
class SeriesBrief:
    """The snapshot, with its new hosts named from the episode's cast. None for a one-off."""

    snapshot: SeriesSnapshot
    new_host_slots: tuple[str, ...]
    new_host_names: tuple[str, ...]
    guest_name: str | None = None
    """011: today's guest, named from the cast."""
    present_names: tuple[tuple[str, str], ...] = ()
    """011: each slot in the episode's cast with its host's name."""

    @classmethod
    def of(cls, snapshot: SeriesSnapshot, cast: Cast) -> "SeriesBrief":
        """A new host who does not take part in this episode (One host) is not named."""
        present = {host.slot: host.name for host in cast.hosts}
        slots = tuple(slot for slot in snapshot.new_host_slots if slot in present)
        guest = present.get(snapshot.guest_slot) if snapshot.guest_slot else None
        names = tuple(present[slot] for slot in slots)
        return cls(snapshot, slots, names, guest, tuple(present.items()))

    @property
    def episode_number(self) -> int:
        return self.snapshot.episode_number

    @property
    def guest_slot(self) -> str | None:
        return self.snapshot.guest_slot if self.guest_name else None

    @property
    def away_host_name(self) -> str | None:
        return self.snapshot.away_host_name

    def is_new_host(self, slot: str) -> bool:
        return slot in self.new_host_slots

    def missed_names(self, line: RememberedLine) -> tuple[str, ...]:
        """The names of this episode's hosts who were not there for `line` (011 R11)."""
        present = dict(self.present_names)
        return tuple(present[slot] for slot in line.missed_by if slot in present)
