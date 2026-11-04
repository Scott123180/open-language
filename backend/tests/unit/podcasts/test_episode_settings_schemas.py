"""011 T065: Episode settings on the start request (contracts §3, data-model §5.1)."""

import pytest
from pydantic import ValidationError

from app.podcasts.schemas import EpisodeSettingsModel, StartEpisodeRequest

DRAFT = {
    "source": "ready_made",
    "show_id": "big-little-questions",
    "title": "Big Little Questions",
    "premise": "Everyday curiosities.",
    "topic": "everyday curiosities",
    "learner_role": "guest",
    "language": "es",
    "hosts": [
        {
            "slot": "lead",
            "name": "Hugo",
            "personality_id": "curious_interviewer",
            "voice_key": "es_ES-davefx-medium",
            "show_role": "host",
        },
        {
            "slot": "second",
            "name": "Inés",
            "personality_id": "expert",
            "voice_key": "es_AR-daniela-high",
            "show_role": "co_host",
        },
    ],
}


def _message(raised: pytest.ExceptionInfo) -> str:
    return raised.value.errors()[0]["msg"].removeprefix("Value error, ")


def test_every_setting_is_optional():
    settings = EpisodeSettingsModel()

    assert (settings.style, settings.line_length, settings.invite_frequency) == (None, None, None)
    assert (settings.learner_role, settings.today_subject) == (None, None)


def test_a_start_request_without_settings_validates():
    request = StartEpisodeRequest(show=DRAFT, format="one_host", length="short")

    assert request.settings is None


@pytest.mark.parametrize(
    ("raw", "kept"),
    [
        ("  why we yawn  ", "why we yawn"),
        ("why we\nyawn", "why we yawn"),
        ("   ", None),
        ("", None),
    ],
)
def test_todays_subject_is_trimmed_folded_and_empty_means_none(raw, kept):
    assert EpisodeSettingsModel(today_subject=raw).today_subject == kept


def test_todays_subject_may_be_120_characters():
    assert len(EpisodeSettingsModel(today_subject="x" * 120).today_subject) == 120


def test_a_longer_subject_is_refused():
    with pytest.raises(ValidationError) as raised:
        EpisodeSettingsModel(today_subject="x" * 121)

    assert _message(raised) == "Today's subject can be at most 120 characters."


@pytest.mark.parametrize(
    ("field", "name"),
    [
        ("style", "style"),
        ("line_length", "host line length"),
        ("invite_frequency", "choice of how often you're asked"),
    ],
)
def test_an_unknown_choice_is_refused_by_name(field, name):
    with pytest.raises(ValidationError) as raised:
        EpisodeSettingsModel(**{field: "loud"})

    assert _message(raised) == f"That {name} isn't in the list. Pick one of the listed ones."


def test_an_unknown_role_is_refused():
    with pytest.raises(ValidationError) as raised:
        EpisodeSettingsModel(learner_role="judge")

    assert _message(raised) == "Your role must be guest, co-host or caller."
