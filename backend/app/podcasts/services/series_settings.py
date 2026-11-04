"""SeriesSettings: a series' usual settings (011 data-model §3.3, research R9).

A series with no settings row has the show's standard settings, built only here. A later
episode keeps a setting for later episodes by naming it in `from_now_on`.
"""

from dataclasses import dataclass, replace
from typing import Protocol

from app.podcasts.catalog import (
    DEFAULT_EPISODE_LENGTH,
    DEFAULT_EPISODE_STYLE,
    DEFAULT_HOST_LINE_LENGTH,
    DEFAULT_INVITE_FREQUENCY,
    DEFAULT_PODCAST_FORMAT,
    SERIES_SETTING_NAMES,
)


class _Show(Protocol):
    learner_role: str


@dataclass(frozen=True, slots=True)
class SeriesSettings:
    format: str
    length: str
    style: str
    line_length: str
    invite_frequency: str
    learner_role: str

    @classmethod
    def standard(cls, show: _Show) -> "SeriesSettings":
        """The show's standard settings: the one definition (FR-019, FR-025)."""
        return cls(
            format=DEFAULT_PODCAST_FORMAT,
            length=DEFAULT_EPISODE_LENGTH,
            style=DEFAULT_EPISODE_STYLE,
            line_length=DEFAULT_HOST_LINE_LENGTH,
            invite_frequency=DEFAULT_INVITE_FREQUENCY,
            learner_role=show.learner_role,
        )

    def with_changes(self, values: "SeriesSettings", names: tuple[str, ...]) -> "SeriesSettings":
        """A copy with the named settings taken from `values`."""
        unknown = [name for name in names if name not in SERIES_SETTING_NAMES]
        if unknown:
            raise ValueError(f"Not a series setting: {', '.join(unknown)}.")
        return replace(self, **{name: getattr(values, name) for name in names})

    def is_standard_for(self, show: _Show) -> bool:
        return self == SeriesSettings.standard(show)
