"""011 T025: ConfiguredTalk, how hosts talk in an episode started with settings (R2–R6, R19–R22)."""

import random

import pytest

from app.conversation_levels import ConversationLevel, with_sentence_rules
from app.podcasts.catalog import (
    EPISODE_LENGTHS,
    INVITE_DEADLINE,
    PERSONALITIES,
    PODCAST_FORMATS,
)
from app.podcasts.prompts import CueContext, PromptContext, ShowBrief, build_standing_prompt
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.episode_settings import EpisodeSettings
from app.podcasts.services.host_talk import ConfiguredTalk, host_talk_for
from app.podcasts.services.series_snapshot import SeriesBrief, SeriesSnapshot
from app.podcasts.services.turn_policy import (
    LEARNER,
    Ask,
    EpisodeState,
    InvitePoint,
    LineCue,
    LineFacts,
)
from app.practice_languages import ConversationLanguages

ONE_HOST, PANEL, LISTEN = (PODCAST_FORMATS[key] for key in ("one_host", "panel", "listen"))
HUGO = Host("lead", "Hugo", "curious_interviewer", "es_ES-davefx-medium", "host")
JULIA = Host("second", "Julia", "expert", "es_AR-daniela-high", "co_host")
PANEL_CAST = Cast.for_format(PANEL, HUGO, JULIA)
ONE_HOST_CAST = Cast.for_format(ONE_HOST, HUGO, None)
SPANISH = ConversationLanguages.of("es", "en")
DEFAULTS = EpisodeSettings.defaults("guest")


def talk(**changes) -> ConfiguredTalk:
    ids = {
        "style": "balanced",
        "line_length": "medium",
        "invite_frequency": "sometimes",
        "learner_role": "guest",
        **changes,
    }
    return ConfiguredTalk(EpisodeSettings.from_ids(**ids))


def cue(intent: str, ask: Ask = Ask.NONE, slot: str = "lead", **fields) -> LineCue:
    return LineCue(slot, intent, ask, False, False, **fields)


def host(slot: str, intent: str = "react", text: str = "Una idea.", **facts) -> LineFacts:
    return LineFacts(slot, intent, text=text, **facts)


def learner(text: str = "Sí.") -> LineFacts:
    return LineFacts(LEARNER, None, text=text)


def state(lines, podcast_format=PANEL, the_talk=None) -> EpisodeState:
    cast = ONE_HOST_CAST if podcast_format.host_count == 1 else PANEL_CAST
    return EpisodeState(
        podcast_format, EPISODE_LENGTHS["short"], cast, tuple(lines), False, the_talk or talk()
    )


def test_any_settings_give_configured_talk():
    assert isinstance(host_talk_for(DEFAULTS), ConfiguredTalk)


def test_the_talk_carries_the_episodes_subject_and_covered_role():
    configured = talk(today_subject="el café", covered_personality="expert")

    assert (configured.today_subject, configured.covered_personality) == ("el café", "expert")


# --- line rules (R5, R19, R20) --------------------------------------------------------------


@pytest.mark.parametrize(
    ("line_length", "count"),
    [("short", "one to two"), ("medium", "three to five"), ("long", "five to eight")],
)
def test_the_line_rules_give_the_host_lines_count(line_length, count):
    rules = talk(line_length=line_length).line_rules("Sam", SPANISH, PANEL_CAST)

    assert (
        f"- Each host line has {count} sentences unless the producer note says otherwise, "
        "each within the rules at the end. Stay in character." in rules
    )
    assert "Keep each line to a few sentences" not in rules


@pytest.mark.parametrize(
    "rule",
    [
        "- When Sam asks a question, answer it first; never answer only with a question.",
        "- Ask Sam something only when the producer note says so, after the line's sentences, "
        "and never what they have already answered.",
        "- The episode has one subject, named in the opening: stay on it until the wrap-up.",
    ],
)
def test_the_line_rules_state_each_configured_rule(rule):
    assert rule in talk().line_rules("Sam", SPANISH, PANEL_CAST).split("\n")


def test_a_panels_line_rules_end_with_the_address_tag_for_the_learner_a_host_or_all():
    last = talk().line_rules("Sam", SPANISH, PANEL_CAST).split("\n")[-1]

    assert last == (
        "- End every line with who it is for: [@Sam], [@Hugo] or [@Julia] for the other host, "
        "or [@all] for no one in particular. The brackets are never read aloud."
    )


def test_one_hosts_address_tag_offers_the_learner_and_all_only():
    last = talk().line_rules("our guest", SPANISH, ONE_HOST_CAST).split("\n")[-1]

    assert last == (
        "- End every line with who it is for: [@our guest], or [@all] for no one in "
        "particular. The brackets are never read aloud."
    )


@pytest.mark.parametrize("level", list(ConversationLevel), ids=lambda level: level.value)
def test_the_speech_rules_are_the_level_sentence_rules(level):
    assert talk().speech_rules("Prompt.", level) == with_sentence_rules("Prompt.", level)


def test_a_configured_speaking_style_replaces_the_personalitys_own():
    expert = PERSONALITIES["expert"]

    assert talk().speaking_style(expert) == expert.configured_speaking_style


def test_a_personality_without_a_configured_style_keeps_its_own():
    joker = PERSONALITIES["joker"]

    assert talk().speaking_style(joker) == joker.speaking_style


# --- cue instructions (R4, R20, R21, R22) ---------------------------------------------------


@pytest.mark.parametrize(
    ("intent", "expected"),
    [
        ("react", "React to the last line and add something of your own, in three sentences."),
        (
            "explain",
            "Explain one thing about today's subject step by step, in four or five sentences: "
            "what it is, how it works, and an everyday example.",
        ),
        (
            "story",
            "Tell a short story or example from your own life about today's subject, in four "
            "or five sentences.",
        ),
        (
            "follow_up",
            "Answer the other question Sam asked before, step by step, in four or five "
            "sentences.",
        ),
    ],
)
def test_each_discussion_kind_has_its_instruction_and_length(intent, expected):
    assert talk().instruction(cue(intent), PANEL_CAST, "Sam", None) == expected


def test_an_answer_names_the_learner_who_asked():
    instruction = talk().instruction(cue("answer", asker=LEARNER), PANEL_CAST, "Sam", None)

    assert instruction == (
        "Answer Sam's question first, step by step, in four or five sentences; if there were "
        "two, answer one."
    )


def test_an_answer_names_the_host_who_asked():
    answer = cue("answer", slot="second", asker="lead")

    assert talk().instruction(answer, PANEL_CAST, "Sam", None).startswith("Answer Hugo's question")


def test_an_answer_to_both_hosts_passes_the_question_on():
    answer = cue("answer", slot="lead", asker=LEARNER, is_for_both=True)

    instruction = talk().instruction(answer, PANEL_CAST, "Sam", None)

    assert instruction.endswith("If it was for you both, answer, then ask Julia too.")


@pytest.mark.parametrize(
    ("line_length", "brief", "full"),
    [
        ("short", "in one or two sentences", "in two sentences"),
        ("long", "in five or six sentences", "in six to eight sentences"),
    ],
)
def test_brief_kinds_take_the_brief_phrase_and_the_rest_the_full_one(line_length, brief, full):
    configured = talk(line_length=line_length)

    assert brief in configured.instruction(cue("react"), PANEL_CAST, "Sam", None)
    assert full in configured.instruction(cue("explain"), PANEL_CAST, "Sam", None)


def test_the_opening_introduces_the_learners_subject():
    configured = talk(today_subject="why we yawn")

    assert configured.instruction(cue("open"), PANEL_CAST, "Sam", None) == (
        "Open the show in four or five sentences: welcome Sam, introduce the show and "
        "yourself, and introduce today's subject."
    )


def test_the_opening_names_one_subject_when_the_learner_gave_none():
    assert talk().instruction(cue("open"), PANEL_CAST, "Sam", None) == (
        "Open the show in four or five sentences: welcome Sam, introduce the show and "
        "yourself, and name today's subject: one concrete question within the topic."
    )


def _series(number: int) -> SeriesBrief:
    return SeriesBrief.of(SeriesSnapshot(number, ("los bostezos",), ()), PANEL_CAST)


def test_a_later_series_opening_names_a_subject_not_in_the_covered_list():
    instruction = talk().instruction(cue("open"), PANEL_CAST, "Sam", _series(3))

    assert "welcome Sam back, say the show is continuing with episode 3" in instruction
    assert instruction.endswith(
        "name today's subject: one concrete question within the topic, not in the covered list."
    )


def test_the_first_series_opening_is_a_one_off_opening():
    configured = talk()

    assert configured.instruction(cue("open"), PANEL_CAST, "Sam", _series(1)) == (
        configured.instruction(cue("open"), PANEL_CAST, "Sam", None)
    )


def test_the_greeting_is_brief():
    greeting = talk().instruction(cue("greet", slot="second"), PANEL_CAST, "Sam", None)

    assert greeting == "Greet Hugo and Sam in three sentences, then introduce yourself."


def test_the_wrap_up_says_the_show_is_nearly_over():
    assert talk().instruction(cue("wrap_up"), PANEL_CAST, "Sam", None) == (
        "Start wrapping up in three sentences: tell Sam the show is nearly over, and sum up "
        "today's subject in one sentence."
    )


def test_the_sign_off_reacts_then_closes_the_show():
    assert talk().instruction(cue("sign_off"), PANEL_CAST, "Sam", None) == (
        "React briefly to the last line, then close the show in three sentences: thank Sam "
        "and say goodbye."
    )


# --- closings (R5, R19, R21) ----------------------------------------------------------------


def test_a_required_line_ends_with_one_question():
    assert talk().closing(cue("react", Ask.REQUIRED), "Sam") == (
        "Then end by asking Sam one question."
    )


def test_a_required_settle_line_asks_the_learner_to_settle_it():
    settle = LineCue("lead", "react", Ask.REQUIRED, False, True)

    assert talk().closing(settle, "Sam") == "Then end by asking Sam to settle it."


def test_an_allowed_line_asks_only_if_it_fits():
    assert talk().closing(cue("react", Ask.ALLOWED), "Sam") == (
        "If it fits, then end by asking Sam one question; if not, ask Sam nothing."
    )


@pytest.mark.parametrize("ask", [Ask.NONE, Ask.NEVER], ids=str)
def test_a_line_that_must_not_ask_says_so(ask):
    assert talk().closing(cue("react", ask), "Sam") == "Don't ask Sam anything this time."


def test_the_wrap_up_asks_for_one_last_thought():
    assert talk().closing(cue("wrap_up", Ask.REQUIRED), "Sam") == (
        "Then ask Sam for one last thought on it."
    )


def test_listens_wrap_up_asks_nothing():
    closing = talk().closing(cue("wrap_up", Ask.NONE), "our listeners")

    assert closing == "Don't ask our listeners anything this time."


# --- asks and invitations (R3, R19) ---------------------------------------------------------


@pytest.mark.parametrize("podcast_format", [ONE_HOST, PANEL], ids=lambda f: f.format_id)
def test_the_deadline_line_is_required(podcast_format):
    assert (
        talk().ask(InvitePoint(INVITE_DEADLINE, podcast_format, "react"), random.Random(0))
        is Ask.REQUIRED
    )


@pytest.mark.parametrize("run", [1, 2, 3])
def test_every_line_is_required_under_often(run):
    often = talk(invite_frequency="often")

    assert often.ask(InvitePoint(run, ONE_HOST, "react"), random.Random(0)) is Ask.REQUIRED


class Constant(random.Random):
    def __init__(self, value: float) -> None:
        super().__init__(0)
        self._value = value

    def random(self) -> float:
        return self._value


@pytest.mark.parametrize(("run", "hazard"), [(1, 0.35), (2, 0.45), (3, 0.55)])
def test_a_hazard_hit_allows_an_invitation_and_a_miss_does_not(run, hazard):
    configured = talk()

    assert configured.ask(InvitePoint(run, PANEL, "react"), Constant(hazard - 0.01)) is Ask.ALLOWED
    assert configured.ask(InvitePoint(run, PANEL, "react"), Constant(hazard + 0.01)) is Ask.NONE


def test_listen_never_asks():
    assert talk().ask(InvitePoint(INVITE_DEADLINE, LISTEN, "react"), random.Random(0)) is Ask.NONE


@pytest.mark.parametrize("intent", ["open", "greet"])
def test_a_two_host_opening_or_greeting_never_invites(intent):
    assert talk().ask(InvitePoint(1, PANEL, intent), Constant(0.0)) is Ask.NEVER


def test_a_one_host_opening_may_invite():
    assert talk().ask(InvitePoint(1, ONE_HOST, "open"), Constant(0.0)) is Ask.ALLOWED


@pytest.mark.parametrize(
    ("ask", "addressee", "invites"),
    [
        (Ask.REQUIRED, None, True),
        (Ask.REQUIRED, "second", True),
        (Ask.ALLOWED, "learner", True),
        (Ask.ALLOWED, None, False),
        (Ask.NONE, "learner", True),
        (Ask.NONE, "second", False),
        (Ask.NEVER, "learner", False),
    ],
)
def test_the_written_line_decides_the_invitation(ask, addressee, invites):
    assert talk().invitation(ask, addressee) is invites


def test_a_configured_line_stores_its_ask_and_addressee():
    assert talk().stored_addressing(Ask.ALLOWED, "learner") == ("allowed", "learner")


# --- discussion intents (R4, R21) -----------------------------------------------------------


def test_a_learner_question_is_answered():
    lines = [host("lead", "open"), host("second", "greet"), learner("¿Por qué bostezamos?")]

    assert talk().discussion_intent(state(lines), Constant(0.99)) == "answer"


def test_a_question_to_the_other_host_is_answered():
    lines = [host("lead", "open"), host("lead", text="¿Y tú, Julia?", addressee="second")]

    assert talk().discussion_intent(state(lines), Constant(0.99)) == "answer"


def test_a_statement_to_the_other_host_is_not_an_answer_cue():
    lines = [host("lead", "open"), host("lead", text="Julia sabe mucho.", addressee="second")]

    assert talk().discussion_intent(state(lines), Constant(0.0)) == "react"


def test_the_second_of_two_learner_questions_gets_a_follow_up():
    lines = [learner("¿Por qué? ¿Y cuándo?"), host("lead", "answer")]

    assert talk().discussion_intent(state(lines), Constant(0.99)) == "follow_up"


@pytest.mark.parametrize(
    ("style", "draw", "intent"),
    [
        ("balanced", 0.54, "react"),
        ("balanced", 0.56, "explain"),
        ("balanced", 0.86, "story"),
        ("presented", 0.34, "react"),
        ("presented", 0.74, "explain"),
        ("presented", 0.76, "story"),
    ],
)
def test_otherwise_the_style_draws_the_kind_of_line(style, draw, intent):
    lines = [host("lead", "open"), host("second", "greet")]

    assert talk(style=style).discussion_intent(state(lines), Constant(draw)) == intent


@pytest.mark.parametrize(
    ("after", "expected"),
    [
        ([learner("Me gustó mucho.")], "sign_off"),
        ([learner("¿Y mañana qué?")], "answer"),
        ([learner("¿Y mañana qué?"), host("lead", "answer")], "sign_off"),
        ([], "sign_off"),
    ],
    ids=["last-thought", "question", "after-the-answer", "passed"],
)
def test_after_the_wrap_up_the_hosts_answer_then_sign_off(after, expected):
    lines = [host("lead", "open"), host("lead", "wrap_up", is_passed=not after), *after]

    assert talk().discussion_intent(state(lines, ONE_HOST), Constant(0.0)) == expected


# --- history replay (R19) ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("addressee", "replayed"),
    [
        ("second", "Hola. [@Julia]"),
        ("lead", "Hola. [@Hugo]"),
        (None, "Hola. [@all]"),
        ("learner", "Hola. [@Sam]"),
    ],
)
def test_a_replayed_line_carries_its_canonical_address_tag(addressee, replayed):
    assert talk().replayed_line("Hola.", addressee, PANEL_CAST, "Sam") == replayed


# --- One host covers the absent second host (R6, R22) ----------------------------------------


SHOW = ShowBrief("Big Little Questions", "Everyday curiosities.", "everyday curiosities", "guest")
COVERED_EXPERT = (
    "This show usually has a second host, the Expert: Knows the facts and likes to explain "
    "them. Today you play that part too: Explains how and why step by step, with simple facts "
    "and an everyday example, and stays precise."
)


def _prompt(configured: ConfiguredTalk, cast: Cast) -> str:
    cues = CueContext(cast, "Sam", configured)
    return build_standing_prompt(PromptContext(SHOW, SPANISH, ConversationLevel.NATURAL, cues))


def test_one_host_covers_the_second_hosts_part_after_the_hosts_section():
    prompt = _prompt(talk(covered_personality="expert"), ONE_HOST_CAST)

    assert COVERED_EXPERT in prompt
    assert prompt.index("Hosts:") < prompt.index(COVERED_EXPERT) < prompt.index("Line rules:")


def test_two_hosts_cover_no_part():
    assert "usually has a second host" not in _prompt(
        talk(covered_personality="expert"), PANEL_CAST
    )


def test_one_host_without_a_covered_personality_covers_no_part():
    assert "usually has a second host" not in _prompt(talk(), ONE_HOST_CAST)


def test_an_unbalancing_line_asks_nothing_before_the_deadline():
    point = InvitePoint(2, PANEL, "react", is_unbalancing=True)

    assert talk().ask(point, Constant(0.0)) is Ask.NONE


def test_often_and_the_deadline_invite_even_when_it_unbalances_the_hosts():
    often = talk(invite_frequency="often")

    assert (
        often.ask(InvitePoint(1, PANEL, "react", is_unbalancing=True), Constant(0.9))
        is Ask.REQUIRED
    )
    assert (
        talk().ask(InvitePoint(4, PANEL, "react", is_unbalancing=True), Constant(0.9))
        is Ask.REQUIRED
    )
