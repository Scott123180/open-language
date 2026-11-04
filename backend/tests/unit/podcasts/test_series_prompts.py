"""010 T033: the series section of the standing prompt, and the series cues (contracts §9, R5, R7)."""

import pytest

from app.conversation_levels import ConversationLevel
from app.podcasts.catalog import (
    HOST_NAME_MAX_LENGTH,
    MAX_REMEMBERED_ABOUT_LEARNER,
    MAX_REMEMBERED_TOPICS,
    PODCAST_FORMATS,
    REMEMBERED_TEXT_BUDGET,
    SERIES_SECTION_MAX_LENGTH,
)
from app.podcasts.prompts import (
    CueContext,
    PromptContext,
    ShowBrief,
    build_standing_prompt,
    render_cue,
)
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.episode_settings import EpisodeSettings
from app.podcasts.services.host_talk import ConfiguredTalk
from app.podcasts.services.series_snapshot import RememberedLine, SeriesBrief, SeriesSnapshot
from app.podcasts.services.turn_policy import Ask, LineCue
from app.practice_languages import ConversationLanguages
from tests.unit.podcasts.legacy_talk_calls import (
    legacy_cue,
    legacy_line_cue,
    legacy_standing_prompt,
)
from tests.unit.podcasts.test_one_off_golden import _golden, golden_cases

HUGO = Host("lead", "Hugo", "curious_interviewer", "es_ES-davefx-medium", "host")
INES = Host("second", "Inés", "expert", "es_AR-daniela-high", "co_host")
CAST = Cast.for_format(PODCAST_FORMATS["panel"], HUGO, INES)
SHOW = ShowBrief("Big Little Questions", "Everyday curiosities.", "everyday curiosities", "guest")
SPANISH = ConversationLanguages.of("es", "en")
TOPICS = ("los bostezos", "el sueño")
LEARNER = ("Odia las mañanas.", "Este fin de semana va a la playa.")
OPEN = legacy_line_cue("lead", "open", True, False, False)


def _brief(number: int = 3, topics=TOPICS, learner=LEARNER, new=(), cast=CAST) -> SeriesBrief:
    return SeriesBrief.of(SeriesSnapshot(number, topics, learner, new), cast)


def _prompt(series: SeriesBrief | None, label: str = "Sam", cast: Cast = CAST) -> str:
    return legacy_standing_prompt(
        show=SHOW,
        cast=cast,
        learner_label=label,
        languages=SPANISH,
        level=ConversationLevel.NATURAL,
        series=series,
    )


def _section(prompt: str) -> str:
    start = prompt.index("This is ")
    return prompt[start : prompt.index("Line rules:")].strip()


# --- the series section --------------------------------------------------------------------


def test_the_series_section_sits_between_the_hosts_and_the_line_rules():
    prompt = _prompt(_brief())

    assert prompt.index("Hosts:") < prompt.index("This is episode 3") < prompt.index("Line rules:")


def test_the_section_opens_with_the_episode_number():
    assert _section(_prompt(_brief())).startswith("This is episode 3 of a continuing show.")


def test_the_first_episode_is_the_first_of_a_continuing_show():
    section = _section(_prompt(_brief(1, (), ())))

    assert section.startswith("This is the first episode of a continuing show.")


def test_the_section_lists_the_topics_covered_and_what_the_learner_said():
    section = _section(_prompt(_brief()))

    assert "Earlier episodes covered: los bostezos; el sueño." in section
    assert "What Sam has told you before:" in section
    assert all(point in section for point in LEARNER)


def test_the_section_states_the_series_rules():
    section = _section(_prompt(_brief())).lower()

    assert "refer back" in section
    assert "not in the covered list" in section
    assert "never claim to remember anything" in section


def test_empty_memory_renders_no_covered_or_told_you_line():
    section = _section(_prompt(_brief(2, (), ())))

    assert "Earlier episodes covered" not in section
    assert "has told you before" not in section
    assert "never claim to remember anything" in section.lower()


def test_listeners_are_spoken_of_in_the_plural():
    assert "What our listeners have told you before:" in _prompt(_brief(), label="our listeners")


def test_the_section_names_languages_never_codes():
    section = _section(_prompt(_brief()))

    assert " es " not in f" {section} " and "(es)" not in section


def test_rendering_the_same_brief_twice_is_identical():
    assert _prompt(_brief()) == _prompt(_brief())


def _worst_case_brief() -> tuple[SeriesBrief, Cast, list[str]]:
    """The caps' worth of points whose texts fill the budget, with the longest names."""
    count = MAX_REMEMBERED_TOPICS + MAX_REMEMBERED_ABOUT_LEARNER
    length = REMEMBERED_TEXT_BUDGET // count
    texts = [f"{index:02d}".ljust(length, "x") for index in range(count)]
    lead = Host("lead", "L" * HOST_NAME_MAX_LENGTH, "enthusiast", "es_ES-davefx-medium", "host")
    second = Host("second", "S" * HOST_NAME_MAX_LENGTH, "expert", "es_AR-daniela-high", "co_host")
    cast = Cast.for_format(PODCAST_FORMATS["panel"], lead, second)
    snapshot = SeriesSnapshot(99, tuple(texts[:10]), tuple(texts[10:]), ("second",))
    return SeriesBrief.of(snapshot, cast), cast, texts


def test_the_worst_stored_set_fits_the_section_budget_with_every_point():
    brief, cast, texts = _worst_case_brief()

    section = _section(_prompt(brief, label="N" * HOST_NAME_MAX_LENGTH, cast=cast))

    assert len(section) <= SERIES_SECTION_MAX_LENGTH
    assert all(text in section for text in texts)


def test_every_point_appears_newest_first():
    section = _section(_prompt(_brief()))

    assert section.index("los bostezos") < section.index("el sueño")
    assert section.index(LEARNER[0]) < section.index(LEARNER[1])


# --- the cues ---------------------------------------------------------------------------------


def test_a_later_open_welcomes_the_learner_back_and_recalls_a_point():
    cue = legacy_cue(cue=OPEN, cast=CAST, learner_label="Sam", series=_brief())

    assert "welcome Sam back" in cue
    assert "continuing" in cue and "episode 3" in cue
    assert "bring up one thing from earlier episodes" in cue


def test_a_later_open_with_nothing_remembered_does_not_ask_for_a_recollection():
    cue = legacy_cue(cue=OPEN, cast=CAST, learner_label="Sam", series=_brief(2, (), ()))

    assert "welcome Sam back" in cue
    assert "earlier episodes" not in cue


def test_the_first_series_episode_opens_as_a_one_off_does():
    assert legacy_cue(
        cue=OPEN, cast=CAST, learner_label="Sam", series=_brief(1, (), ())
    ) == legacy_cue(cue=OPEN, cast=CAST, learner_label="Sam")


@pytest.mark.parametrize("intent", ["greet", "discuss", "wrap_up", "sign_off"])
def test_the_other_cues_are_unchanged_in_a_series(intent):
    cue = legacy_line_cue("second" if intent == "greet" else "lead", intent, False, False, False)

    assert legacy_cue(cue=cue, cast=CAST, learner_label="Sam", series=_brief()) == legacy_cue(
        cue=cue, cast=CAST, learner_label="Sam"
    )


# --- one-off: series=None is 007's text ----------------------------------------------------


@pytest.mark.parametrize(("key", "render"), list(golden_cases()), ids=lambda value: str(value))
def test_an_explicit_series_none_is_the_007_text(key, render, monkeypatch):
    golden = "tests.unit.podcasts.test_one_off_golden"
    monkeypatch.setattr(
        f"{golden}.legacy_standing_prompt",
        lambda **args: legacy_standing_prompt(**args, series=None),
    )
    monkeypatch.setattr(f"{golden}.legacy_cue", lambda **args: legacy_cue(**args, series=None))

    assert render() == _golden()[key]


# --- US3: a new host ----------------------------------------------------------------------


def test_the_section_introduces_a_new_host_as_new_to_the_show():
    section = _section(_prompt(_brief(new=("second",))))

    assert "Inés is new to the show" in section
    assert "does not know the earlier episodes" in section
    assert "introduce Inés as new" in section


def test_a_new_hosts_greeting_introduces_them_as_new():
    greet = legacy_line_cue("second", "greet", False, False, False)

    cue = legacy_cue(cue=greet, cast=CAST, learner_label="Sam", series=_brief(new=("second",)))

    assert "introduce yourself as new to the show" in cue


def test_an_old_hosts_greeting_is_unchanged():
    greet = legacy_line_cue("second", "greet", False, False, False)

    assert legacy_cue(cue=greet, cast=CAST, learner_label="Sam", series=_brief()) == legacy_cue(
        cue=greet, cast=CAST, learner_label="Sam"
    )


def test_a_new_lead_opens_by_introducing_themselves_as_the_new_host():
    cue = legacy_cue(cue=OPEN, cast=CAST, learner_label="Sam", series=_brief(new=("lead",)))

    assert "Introduce yourself as the show's new host." in cue


# --- 011 T092: today's guest, and a host new after a switch to Panel (R10, R12) -----------

MARCO = Host("second", "Marco", "joker", "es_AR-daniela-high", "co_host")
GUEST_CAST = Cast.for_format(PODCAST_FORMATS["panel"], HUGO, MARCO)


def _configured(series: SeriesBrief, cast: Cast) -> CueContext:
    settings = EpisodeSettings.defaults("guest")
    return CueContext(cast, "Sam", ConfiguredTalk(settings), series)


def _guest_brief(cast: Cast = GUEST_CAST, guest_slot="second", new=()) -> SeriesBrief:
    snapshot = SeriesSnapshot(4, TOPICS, LEARNER, new, guest_slot=guest_slot)
    return SeriesBrief.of(snapshot, cast)


def _configured_prompt(series: SeriesBrief, cast: Cast = GUEST_CAST) -> str:
    context = _configured(series, cast)
    return build_standing_prompt(PromptContext(SHOW, SPANISH, ConversationLevel.NATURAL, context))


def test_a_guest_joins_for_this_episode_without_knowing_the_earlier_ones():
    section = _section(_configured_prompt(_guest_brief()))

    assert (
        "- Marco is today's guest, here for this episode only, and does not know the earlier "
        "episodes." in section
    )


def test_the_open_cue_names_todays_guest():
    cue = LineCue("lead", "open", Ask.NEVER, False, False)

    text = render_cue(cue, _configured(_guest_brief(), GUEST_CAST))

    assert "Introduce Marco as today's guest." in text


def test_the_guests_greeting_introduces_them_as_todays_guest():
    cue = LineCue("second", "greet", Ask.NEVER, False, False)

    text = render_cue(cue, _configured(_guest_brief(), GUEST_CAST))

    assert "then introduce yourself as today's guest." in text


def test_a_host_who_joins_on_a_switch_to_panel_is_introduced_as_new():
    brief = SeriesBrief.of(SeriesSnapshot(4, TOPICS, LEARNER, ("second",)), CAST)

    section = _section(_configured_prompt(brief, CAST))

    assert "- Inés is new to the show and does not know the earlier episodes" in section


def test_without_a_guest_the_configured_section_has_no_guest_line():
    brief = SeriesBrief.of(SeriesSnapshot(4, TOPICS, LEARNER), CAST)

    assert "today's guest" not in _configured_prompt(brief, CAST)


# --- 011 T116: the away host, the lead stand-in and the missed marks (R10, R11) -----------

CLARA_AWAY = SeriesSnapshot(5, TOPICS, LEARNER, guest_slot="second", away_host_name="Clara")
MARKS_RULE = (
    "- Inés only heard about points marked [Inés was away]: Inés may mention them as something "
    "heard from the other host, never as having been there or having heard Sam say it."
)


def test_the_away_host_is_away_today_never_gone():
    section = _section(_configured_prompt(SeriesBrief.of(CLARA_AWAY, GUEST_CAST)))

    assert "- Clara is away today and back next time." in section
    assert "left" not in section


def test_the_open_cue_names_the_guest_and_the_away_host():
    cue = LineCue("lead", "open", Ask.NEVER, False, False)

    text = render_cue(cue, _configured(SeriesBrief.of(CLARA_AWAY, GUEST_CAST), GUEST_CAST))

    assert "Introduce Marco as today's guest, in for Clara, who is away today." in text


def test_a_lead_guest_opens_as_standing_in_for_the_away_host():
    marco_lead = Host("lead", "Marco", "joker", "es_AR-daniela-high", "host")
    cast = Cast.for_format(PODCAST_FORMATS["one_host"], marco_lead, None)
    snapshot = SeriesSnapshot(5, TOPICS, LEARNER, guest_slot="lead", away_host_name="Hugo")
    cue = LineCue("lead", "open", Ask.NEVER, False, False)

    text = render_cue(cue, _configured(SeriesBrief.of(snapshot, cast), cast))

    assert "You are today's guest host, standing in for Hugo, who is away today." in text


def test_a_marked_point_names_who_was_away_and_adds_the_rule():
    marked = SeriesSnapshot(5, (RememberedLine("los bostezos", ("second",)),), LEARNER)

    section = _section(_configured_prompt(SeriesBrief.of(marked, CAST), CAST))

    assert "Earlier episodes covered: los bostezos [Inés was away for this]." in section
    assert MARKS_RULE in section


def test_the_marks_rule_appears_only_when_a_point_is_marked():
    section = _section(
        _configured_prompt(SeriesBrief.of(SeriesSnapshot(5, TOPICS, LEARNER), CAST), CAST)
    )

    assert "only heard about" not in section
