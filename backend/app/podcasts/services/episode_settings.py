"""EpisodeSettings: how one episode sounds, frozen when it starts (data-model §3.1, FR-012).

Behaviour reads the catalogue entries it holds, never ids. An episode stored without settings
is pre-011, and only `host_talk_for` turns that fact into behaviour (research R1).
"""

from dataclasses import dataclass

from app.podcasts.catalog import (
    DEFAULT_EPISODE_STYLE,
    DEFAULT_HOST_LINE_LENGTH,
    DEFAULT_INVITE_FREQUENCY,
    EPISODE_STYLES,
    HOST_LINE_LENGTHS,
    INVITE_FREQUENCIES,
    EpisodeStyle,
    HostLineLength,
    InviteFrequency,
)

_SUMMARY_SEPARATOR = " · "


@dataclass(frozen=True, slots=True)
class EpisodeSettings:
    style: EpisodeStyle
    line_length: HostLineLength
    invite_frequency: InviteFrequency
    learner_role: str
    today_subject: str | None = None
    covered_personality: str | None = None
    """One host only: the personality of the second host the one host stands in for (R6)."""

    @classmethod
    def defaults(cls, learner_role: str) -> "EpisodeSettings":
        return cls.from_ids(
            style=DEFAULT_EPISODE_STYLE,
            line_length=DEFAULT_HOST_LINE_LENGTH,
            invite_frequency=DEFAULT_INVITE_FREQUENCY,
            learner_role=learner_role,
        )

    @classmethod
    def from_ids(
        cls,
        *,
        style: str,
        line_length: str,
        invite_frequency: str,
        learner_role: str,
        today_subject: str | None = None,
        covered_personality: str | None = None,
    ) -> "EpisodeSettings":
        """Resolve stored or requested ids. Raises ValueError naming an unknown setting."""
        return cls(
            style=_entry(EPISODE_STYLES, "style", style),
            line_length=_entry(HOST_LINE_LENGTHS, "line_length", line_length),
            invite_frequency=_entry(INVITE_FREQUENCIES, "invite_frequency", invite_frequency),
            learner_role=learner_role,
            today_subject=today_subject,
            covered_personality=covered_personality,
        )

    def summary(self) -> str:
        """The setup's one-line summary: "Balanced · Medium lines · Asked sometimes"."""
        asked = f"Asked {self.invite_frequency.label.lower()}"
        lines = f"{self.line_length.label} lines"
        return _SUMMARY_SEPARATOR.join((self.style.label, lines, asked))


def _entry(catalogue, setting: str, entry_id: str):
    if entry_id not in catalogue:
        raise ValueError(f"Unknown {setting}: {entry_id!r}.")
    return catalogue[entry_id]
