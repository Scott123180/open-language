"""T017: the standing prompt and the producer cues (research R3, R5, R14)."""

import itertools
import re

import pytest

from app.conversation_levels import ConversationLevel, with_partner_speech_rules
from app.podcasts.catalog import PERSONALITIES, PODCAST_FORMATS, SHOW_TEMPLATES
from app.podcasts.prompts import (
    PRODUCER_NOTE_MARKER,
    CueContext,
    PromptContext,
    ShowBrief,
    build_standing_prompt,
    learner_label_for,
)
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.episode_settings import EpisodeSettings
from app.podcasts.services.host_talk import ConfiguredTalk
from app.podcasts.services.series_snapshot import SeriesBrief, SeriesSnapshot
from app.practice_languages import ConversationLanguages
from tests.unit.podcasts.legacy_talk_calls import (
    legacy_cue,
    legacy_line_cue,
    legacy_standing_prompt,
)

CHARACTERS_PER_TOKEN = 4
STANDING_PROMPT_TOKEN_BUDGET = 700
CUE_TOKEN_BUDGET = 40
PANEL = PODCAST_FORMATS["panel"]
ONE_HOST = PODCAST_FORMATS["one_host"]
LUCIA = Host("lead", "Lucía", "enthusiast", "es_AR-daniela-high", "host")
MARCO = Host("second", "Marco", "dry_sceptic", "es_ES-davefx-medium", "co_host")
CAST = Cast.for_format(PANEL, LUCIA, MARCO)
SHOW = ShowBrief(
    title="Weekend Food Talk",
    premise="Two food lovers swap weekend cooking wins and disasters.",
    topic="food",
    learner_role="guest",
)
SPANISH = ConversationLanguages.of("es", "en")


def _prompt(learner_label="our guest", level=ConversationLevel.NATURAL, cast=CAST, show=SHOW):
    return legacy_standing_prompt(
        show=show, cast=cast, learner_label=learner_label, languages=SPANISH, level=level
    )


def _tokens(text: str) -> float:
    return len(text) / CHARACTERS_PER_TOKEN


# --- learner label ----------------------------------------------------------------------


def test_the_learner_is_our_guest_without_a_name():
    assert learner_label_for(ONE_HOST, None) == "our guest"


def test_the_learner_is_called_by_their_name():
    assert learner_label_for(PANEL, "Sam") == "Sam"


def test_listeners_are_addressed_in_listen():
    assert learner_label_for(PODCAST_FORMATS["listen"], "Sam") == "our listeners"


# --- standing prompt --------------------------------------------------------------------


def test_the_language_rule_names_languages_never_codes():
    prompt = _prompt()

    assert "CRITICAL LANGUAGE RULE" in prompt
    assert "Spanish" in prompt and "English" in prompt
    assert not re.search(r"\b(es|en)\b", prompt)


def test_the_show_is_described():
    prompt = _prompt()

    assert SHOW.title in prompt and SHOW.premise in prompt and "guest" in prompt


@pytest.mark.parametrize("host", [LUCIA, MARCO], ids=["lead", "second"])
def test_every_host_is_described(host):
    personality = PERSONALITIES[host.personality_id]
    prompt = _prompt()

    assert host.name in prompt
    assert personality.description in prompt
    assert personality.speaking_style in prompt
    assert host.show_role.replace("_", "-") in prompt


def test_one_host_describes_only_the_lead():
    prompt = _prompt(cast=Cast.for_format(ONE_HOST, LUCIA, None))

    assert "Lucía" in prompt and "Marco" not in prompt


def test_a_hosts_angle_is_given_when_it_has_one():
    angled = Host("lead", "Lucía", "enthusiast", "es_AR-daniela-high", "host", "Loves street food")

    assert "Loves street food" in _prompt(cast=Cast.for_format(PANEL, angled, MARCO))


@pytest.mark.parametrize(
    "rule",
    [
        "Write only the words of the host named in the producer note",
        "No name label",
        "no stage directions",
        "Never write lines for another host or for our guest",
        "Address the learner as our guest",
        "Producer notes are never read aloud or mentioned",
    ],
)
def test_the_line_rules_are_stated(rule):
    assert rule in _prompt()


def test_the_learner_is_addressed_by_the_label_given():
    assert "Address the learner as Sam" in _prompt(learner_label="Sam")


def test_a_learner_writing_in_english_is_answered_in_the_practice_language():
    assert (
        "If our guest writes in English, answer in Spanish and invite them, in character, "
        "to use Spanish." in _prompt()
    )


def test_the_level_rules_come_last():
    beginner = _prompt(level=ConversationLevel.BEGINNER)

    assert beginner == with_partner_speech_rules(_prompt(), ConversationLevel.BEGINNER)
    assert beginner != _prompt()


def test_at_natural_the_prompt_is_unlevelled():
    assert with_partner_speech_rules(_prompt(), ConversationLevel.NATURAL) == _prompt()


def test_the_longest_show_with_its_longest_hosts_fits_the_budget():
    show = max(SHOW_TEMPLATES.values(), key=lambda s: len(s.title) + len(s.premise))
    wordiest = sorted(
        PERSONALITIES.values(), key=lambda p: len(p.description) + len(p.speaking_style)
    )[-2:]
    lead = Host("lead", "Maximiliana", wordiest[0].personality_id, "v1", "host", "An angle.")
    second = Host("second", "Bartholomäus", wordiest[1].personality_id, "v2", "guest_expert")
    brief = ShowBrief(show.title, show.premise, show.topic, show.learner_role)

    prompt = _prompt(
        learner_label="our guest",
        level=ConversationLevel.BEGINNER,
        cast=Cast.for_format(PANEL, lead, second),
        show=brief,
    )

    assert _tokens(prompt) <= STANDING_PROMPT_TOKEN_BUDGET


# --- cues -------------------------------------------------------------------------------

INTENTS = ("open", "greet", "discuss", "wrap_up", "sign_off")


def _cue(slot="second", intent="discuss", invites=False, after_pass=False, settle=False):
    return legacy_line_cue(slot, intent, invites, after_pass, settle)


def test_a_cue_begins_with_the_producer_note_marker():
    assert legacy_cue(cue=_cue(), cast=CAST, learner_label="our guest").startswith(
        PRODUCER_NOTE_MARKER
    )


def test_a_cue_names_the_speaking_host():
    assert "Next: Marco." in legacy_cue(
        cue=_cue(slot="second"), cast=CAST, learner_label="our guest"
    )
    assert "Next: Lucía." in legacy_cue(cue=_cue(slot="lead"), cast=CAST, learner_label="our guest")


@pytest.mark.parametrize("intent", INTENTS)
def test_every_intent_has_its_own_instruction(intent):
    rendered = {
        legacy_cue(cue=_cue(intent=other), cast=CAST, learner_label="our guest")
        for other in INTENTS
    }

    assert len(rendered) == len(INTENTS)
    assert legacy_cue(cue=_cue(intent=intent), cast=CAST, learner_label="our guest")


def test_only_an_inviting_cue_asks_the_learner_a_question():
    assert "End by asking our guest" in legacy_cue(
        cue=_cue(invites=True), cast=CAST, learner_label="our guest"
    )
    assert "End by asking" not in legacy_cue(
        cue=_cue(invites=False), cast=CAST, learner_label="our guest"
    )


def test_a_settle_invite_asks_the_learner_to_settle_it():
    rendered = legacy_cue(cue=_cue(invites=True, settle=True), cast=CAST, learner_label="Sam")

    assert "End by asking Sam to settle it." in rendered


def test_a_cue_after_a_pass_says_not_to_wait_for_the_learner():
    assert "Don't wait for our guest." in legacy_cue(
        cue=_cue(after_pass=True), cast=CAST, learner_label="our guest"
    )


def _is_reachable(intent, invites, after_pass, settle, label) -> bool:
    """Cues the policy can produce: listeners are never invited, the opening and the greeting
    never follow a pass, a sign-off never invites, and only an invitation can be a settle."""
    return not (
        (invites and label == "our listeners")
        or (after_pass and intent in ("open", "greet"))
        or (invites and intent == "sign_off")
        or (settle and not invites)
    )


@pytest.mark.parametrize(
    ("intent", "invites", "after_pass", "settle", "label"),
    [
        combination
        for combination in itertools.product(
            INTENTS, (False, True), (False, True), (False, True), ("our guest", "our listeners")
        )
        if _is_reachable(*combination)
    ],
)
def test_every_cue_fits_the_budget(intent, invites, after_pass, settle, label):
    rendered = legacy_cue(
        cue=_cue("second", intent, invites, after_pass, settle), cast=CAST, learner_label=label
    )

    assert _tokens(rendered) <= CUE_TOKEN_BUDGET


# --- 011 T069: Today's subject and the episode's role (research R5, plan interpretation 13) ---


SUBJECT_SENTENCE = (
    "Today's subject, chosen by Sam: why we yawn. Talk about it within the show's topic."
)
COVERED_RULE = "- Choose a subject within the show's topic that is not in the covered list."
CHOSEN_RULE = "- Today's subject was chosen by Sam: talk about it even if it was covered before."


def _configured(subject=None, role="guest", series=None) -> str:
    settings = EpisodeSettings.from_ids(
        style="balanced",
        line_length="medium",
        invite_frequency="sometimes",
        learner_role=role,
        today_subject=subject,
    )
    show = ShowBrief("Weekend Food Talk", "Food.", "food", role)
    cues = CueContext(CAST, "Sam", ConfiguredTalk(settings), series)
    return build_standing_prompt(PromptContext(show, SPANISH, ConversationLevel.NATURAL, cues))


def _series(number: int = 3) -> SeriesBrief:
    return SeriesBrief.of(SeriesSnapshot(number, ("el pan",), ()), CAST)


def test_todays_subject_is_named_in_the_show_section():
    prompt = _configured("why we yawn")

    assert SUBJECT_SENTENCE in prompt
    assert prompt.index(SUBJECT_SENTENCE) < prompt.index("Hosts:")


def test_the_learners_role_is_the_episodes():
    assert "Sam is a caller who has phoned in to the show." in _configured(role="caller")


def test_a_series_episode_with_a_subject_may_talk_about_a_covered_subject():
    prompt = _configured("el pan", series=_series())

    assert CHOSEN_RULE in prompt
    assert COVERED_RULE not in prompt


def test_without_a_subject_the_prompt_has_no_subject_lines():
    prompt = _configured(series=_series())

    assert "Today's subject" not in prompt
    assert COVERED_RULE in prompt
