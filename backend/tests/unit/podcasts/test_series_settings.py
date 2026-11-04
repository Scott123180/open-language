"""011 T086: SeriesSettings, a series' usual settings (data-model §3.3)."""

from dataclasses import FrozenInstanceError, replace

import pytest

from app.podcasts.catalog import SERIES_SETTING_NAMES
from app.podcasts.services.series_settings import SeriesSettings
from app.podcasts.services.series_storage import ShowContent

SHOW = ShowContent.ready_made("tech-for-normal-people")


def test_the_standard_settings_are_one_host_medium_balanced_medium_sometimes_and_the_shows_role():
    assert SeriesSettings.standard(SHOW) == SeriesSettings(
        format="one_host",
        length="medium",
        style="balanced",
        line_length="medium",
        invite_frequency="sometimes",
        learner_role="caller",
    )


def test_with_changes_copies_only_the_named_settings():
    usual = SeriesSettings.standard(SHOW)
    episode = replace(usual, format="panel", style="presented", length="long")

    changed = usual.with_changes(episode, ("style",))

    assert changed == replace(usual, style="presented")


def test_every_series_setting_can_be_kept():
    usual = SeriesSettings.standard(SHOW)
    episode = SeriesSettings("panel", "long", "presented", "long", "rarely", "guest")

    assert usual.with_changes(episode, SERIES_SETTING_NAMES) == episode


def test_an_unknown_name_is_refused():
    usual = SeriesSettings.standard(SHOW)

    with pytest.raises(ValueError, match="today_subject"):
        usual.with_changes(usual, ("today_subject",))


def test_standard_is_known_until_anything_changes():
    usual = SeriesSettings.standard(SHOW)

    assert usual.is_standard_for(SHOW)
    assert not replace(usual, invite_frequency="often").is_standard_for(SHOW)


def test_the_settings_are_frozen():
    with pytest.raises(FrozenInstanceError):
        SeriesSettings.standard(SHOW).style = "presented"
