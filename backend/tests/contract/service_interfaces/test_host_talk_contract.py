"""011 T009: HostTalk is an ABC, and every implementation keeps its contract (research R1, LSP).

`host_talk_for` is the one place an episode's settings become behaviour: no settings row means
`LegacyTalk`, today's behaviour byte for byte.
"""

import random
from abc import ABC

import pytest

from app.conversation_levels import ConversationLevel
from app.podcasts.catalog import EPISODE_LENGTHS, INVITE_DEADLINE, PERSONALITIES, PODCAST_FORMATS
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.episode_settings import EpisodeSettings
from app.podcasts.services.host_talk import ConfiguredTalk, HostTalk, LegacyTalk, host_talk_for
from app.podcasts.services.turn_policy import Ask, EpisodeState, InvitePoint, LineCue, LineFacts
from app.practice_languages import ConversationLanguages

METHODS = {
    "ask",
    "invitation",
    "stored_addressing",
    "discussion_intent",
    "line_rules",
    "speech_rules",
    "speaking_style",
    "instruction",
    "closing",
    "replayed_line",
}
SPEAKING_FORMATS = [f for f in PODCAST_FORMATS.values() if f.is_learner_speaking]
HUGO = Host("lead", "Hugo", "curious_interviewer", "es_ES-davefx-medium", "host")
JULIA = Host("second", "Julia", "expert", "es_AR-daniela-high", "co_host")
PANEL = PODCAST_FORMATS["panel"]
CAST = Cast.for_format(PANEL, HUGO, JULIA)
SPANISH = ConversationLanguages.of("es", "en")
REQUIRED_CUE = LineCue("lead", "wrap_up", Ask.REQUIRED, False, False)
INTENT_COLUMN_LENGTH = 10


def implementations() -> list[HostTalk]:
    return [LegacyTalk(), ConfiguredTalk(EpisodeSettings.defaults("guest"))]


def _state(talk: HostTalk) -> EpisodeState:
    lines = (
        LineFacts("lead", "open", text="¡Hola a todos!", message_id=1),
        LineFacts("second", "greet", text="¡Hola, Hugo!", message_id=2),
    )
    return EpisodeState(PANEL, EPISODE_LENGTHS["short"], CAST, lines, False, talk=talk)


def test_host_talk_is_an_abc_declaring_exactly_its_methods():
    assert issubclass(HostTalk, ABC)
    assert HostTalk.__abstractmethods__ == frozenset(METHODS)


def test_no_settings_row_means_legacy_talk():
    assert isinstance(host_talk_for(None), LegacyTalk)


@pytest.mark.parametrize("talk", implementations(), ids=type)
@pytest.mark.parametrize("podcast_format", SPEAKING_FORMATS, ids=lambda f: f.format_id)
def test_the_deadline_line_is_required_to_invite(talk, podcast_format):
    ask = talk.ask(InvitePoint(INVITE_DEADLINE, podcast_format, "react"), random.Random(1))

    assert ask is Ask.REQUIRED


@pytest.mark.parametrize("talk", implementations(), ids=type)
def test_a_required_line_invites_and_a_none_line_without_an_addressee_does_not(talk):
    assert talk.invitation(Ask.REQUIRED, None) is True
    assert talk.invitation(Ask.NONE, None) is False


@pytest.mark.parametrize("talk", implementations(), ids=type)
@pytest.mark.parametrize("level", list(ConversationLevel), ids=lambda level: level.value)
def test_the_natural_level_leaves_the_prompt_unchanged(talk, level):
    rendered = talk.speech_rules("Prompt.", level)

    if level is ConversationLevel.NATURAL:
        assert rendered == "Prompt."
    else:
        assert rendered.startswith("Prompt.")


@pytest.mark.parametrize("talk", implementations(), ids=type)
def test_the_text_pieces_are_never_empty(talk):
    assert talk.line_rules("Sam", SPANISH, CAST)
    assert talk.speaking_style(PERSONALITIES["expert"])
    assert talk.closing(REQUIRED_CUE, "Sam")
    assert talk.instruction(REQUIRED_CUE, CAST, "Sam", None)


@pytest.mark.parametrize("talk", implementations(), ids=type)
def test_a_replayed_line_starts_with_its_stored_text(talk):
    assert talk.replayed_line("¡Hola!", None, CAST, "Sam").startswith("¡Hola!")


@pytest.mark.parametrize("talk", implementations(), ids=type)
def test_a_discussion_intent_fits_the_intent_column(talk):
    for seed in range(20):
        intent = talk.discussion_intent(_state(talk), random.Random(seed))

        assert len(intent) <= INTENT_COLUMN_LENGTH


@pytest.mark.parametrize("talk", implementations(), ids=type)
def test_no_talk_carries_a_subject_or_covered_role_by_default(talk):
    if isinstance(talk, LegacyTalk):
        assert (talk.today_subject, talk.covered_personality) == (None, None)


# --- LegacyTalk only: today's behaviour --------------------------------------------------


@pytest.mark.parametrize("podcast_format", SPEAKING_FORMATS, ids=lambda f: f.format_id)
def test_legacy_talk_never_allows_an_optional_invitation(podcast_format):
    talk = LegacyTalk()

    asks = {
        talk.ask(InvitePoint(run, podcast_format, "discuss"), random.Random(seed))
        for run in range(1, INVITE_DEADLINE + 1)
        for seed in range(40)
    }

    assert Ask.ALLOWED not in asks


@pytest.mark.parametrize("ask", list(Ask), ids=str)
def test_legacy_talk_invites_exactly_on_a_required_line(ask):
    assert LegacyTalk().invitation(ask, "learner") is (ask is Ask.REQUIRED)


@pytest.mark.parametrize("personality", list(PERSONALITIES.values()), ids=lambda p: p.label)
def test_legacy_talk_keeps_every_speaking_style(personality):
    assert LegacyTalk().speaking_style(personality) == personality.speaking_style


def test_legacy_talk_replays_a_line_unchanged():
    assert LegacyTalk().replayed_line("¿Y tú?", "learner", CAST, "Sam") == "¿Y tú?"


def test_legacy_talk_listens_without_inviting():
    listen = PODCAST_FORMATS["listen"]

    assert (
        LegacyTalk().ask(InvitePoint(INVITE_DEADLINE, listen, "discuss"), random.Random(1))
        is Ask.NONE
    )


def test_legacy_talk_holds_back_an_unbalancing_invitation_before_the_deadline():
    talk = LegacyTalk()

    assert talk.ask(InvitePoint(2, PANEL, "discuss", True), random.Random(1)) is Ask.NONE
    assert talk.ask(InvitePoint(4, PANEL, "discuss", True), random.Random(1)) is Ask.REQUIRED
