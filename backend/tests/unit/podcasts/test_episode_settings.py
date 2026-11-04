"""011 T008: EpisodeSettings, how one episode sounds, frozen at Start (data-model §3.1)."""

from dataclasses import FrozenInstanceError

import pytest

from app.podcasts.catalog import EPISODE_STYLES, HOST_LINE_LENGTHS, INVITE_FREQUENCIES
from app.podcasts.services.episode_settings import EpisodeSettings


def _presented_long_rarely(**changes) -> EpisodeSettings:
    arguments = {
        "style": "presented",
        "line_length": "long",
        "invite_frequency": "rarely",
        "learner_role": "caller",
        "today_subject": "por qué bostezamos",
        "covered_personality": "expert",
        **changes,
    }
    return EpisodeSettings.from_ids(**arguments)


def test_the_defaults_are_balanced_medium_and_sometimes_with_the_given_role():
    settings = EpisodeSettings.defaults("guest")

    assert settings.style is EPISODE_STYLES["balanced"]
    assert settings.line_length is HOST_LINE_LENGTHS["medium"]
    assert settings.invite_frequency is INVITE_FREQUENCIES["sometimes"]
    assert settings.learner_role == "guest"
    assert (settings.today_subject, settings.covered_personality) == (None, None)


def test_from_ids_resolves_every_catalogue_entry():
    settings = _presented_long_rarely()

    assert settings.style is EPISODE_STYLES["presented"]
    assert settings.line_length is HOST_LINE_LENGTHS["long"]
    assert settings.invite_frequency is INVITE_FREQUENCIES["rarely"]
    assert settings.learner_role == "caller"
    assert settings.today_subject == "por qué bostezamos"
    assert settings.covered_personality == "expert"


@pytest.mark.parametrize("setting", ["style", "line_length", "invite_frequency"])
def test_an_unknown_id_is_refused_naming_the_setting(setting):
    with pytest.raises(ValueError, match=setting):
        _presented_long_rarely(**{setting: "loud"})


def test_the_summary_of_the_defaults_reads_as_one_line():
    assert (
        EpisodeSettings.defaults("guest").summary() == "Balanced · Medium lines · Asked sometimes"
    )


def test_the_summary_names_each_chosen_setting():
    assert _presented_long_rarely().summary() == "Presented · Long lines · Asked rarely"


def test_the_settings_are_frozen():
    settings = EpisodeSettings.defaults("guest")

    with pytest.raises(FrozenInstanceError):
        settings.learner_role = "caller"
