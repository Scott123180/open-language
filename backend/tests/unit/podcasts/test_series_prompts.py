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
from app.podcasts.prompts import ShowBrief, build_standing_prompt, render_cue
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.series_snapshot import SeriesBrief, SeriesSnapshot
from app.podcasts.services.turn_policy import LineCue
from app.practice_languages import ConversationLanguages
from tests.unit.podcasts.test_one_off_golden import _golden, golden_cases

HUGO = Host("lead", "Hugo", "curious_interviewer", "es_ES-davefx-medium", "host")
INES = Host("second", "Inés", "expert", "es_AR-daniela-high", "co_host")
CAST = Cast.for_format(PODCAST_FORMATS["panel"], HUGO, INES)
SHOW = ShowBrief("Big Little Questions", "Everyday curiosities.", "everyday curiosities", "guest")
SPANISH = ConversationLanguages.of("es", "en")
TOPICS = ("los bostezos", "el sueño")
LEARNER = ("Odia las mañanas.", "Este fin de semana va a la playa.")
OPEN = LineCue("lead", "open", True, False, False)


def _brief(number: int = 3, topics=TOPICS, learner=LEARNER, new=(), cast=CAST) -> SeriesBrief:
    return SeriesBrief.of(SeriesSnapshot(number, topics, learner, new), cast)


def _prompt(series: SeriesBrief | None, label: str = "Sam", cast: Cast = CAST) -> str:
    return build_standing_prompt(
        SHOW, cast, label, SPANISH, ConversationLevel.NATURAL, series=series
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
    cue = render_cue(OPEN, CAST, "Sam", series=_brief())

    assert "welcome Sam back" in cue
    assert "continuing" in cue and "episode 3" in cue
    assert "bring up one thing from earlier episodes" in cue


def test_a_later_open_with_nothing_remembered_does_not_ask_for_a_recollection():
    cue = render_cue(OPEN, CAST, "Sam", series=_brief(2, (), ()))

    assert "welcome Sam back" in cue
    assert "earlier episodes" not in cue


def test_the_first_series_episode_opens_as_a_one_off_does():
    assert render_cue(OPEN, CAST, "Sam", series=_brief(1, (), ())) == render_cue(OPEN, CAST, "Sam")


@pytest.mark.parametrize("intent", ["greet", "discuss", "wrap_up", "sign_off"])
def test_the_other_cues_are_unchanged_in_a_series(intent):
    cue = LineCue("second" if intent == "greet" else "lead", intent, False, False, False)

    assert render_cue(cue, CAST, "Sam", series=_brief()) == render_cue(cue, CAST, "Sam")


# --- one-off: series=None is 007's text ----------------------------------------------------


@pytest.mark.parametrize(("key", "render"), list(golden_cases()), ids=lambda value: str(value))
def test_an_explicit_series_none_is_the_007_text(key, render, monkeypatch):
    import app.podcasts.prompts as prompts

    standing, cue = prompts.build_standing_prompt, prompts.render_cue
    monkeypatch.setattr(
        "tests.unit.podcasts.test_one_off_golden.build_standing_prompt",
        lambda *args: standing(*args, series=None),
    )
    monkeypatch.setattr(
        "tests.unit.podcasts.test_one_off_golden.render_cue", lambda *args: cue(*args, series=None)
    )

    assert render() == _golden()[key]


# --- US3: a new host ----------------------------------------------------------------------


def test_the_section_introduces_a_new_host_as_new_to_the_show():
    section = _section(_prompt(_brief(new=("second",))))

    assert "Inés is new to the show" in section
    assert "does not know the earlier episodes" in section
    assert "introduce Inés as new" in section


def test_a_new_hosts_greeting_introduces_them_as_new():
    greet = LineCue("second", "greet", False, False, False)

    cue = render_cue(greet, CAST, "Sam", series=_brief(new=("second",)))

    assert "introduce yourself as new to the show" in cue


def test_an_old_hosts_greeting_is_unchanged():
    greet = LineCue("second", "greet", False, False, False)

    assert render_cue(greet, CAST, "Sam", series=_brief()) == render_cue(greet, CAST, "Sam")


def test_a_new_lead_opens_by_introducing_themselves_as_the_new_host():
    cue = render_cue(OPEN, CAST, "Sam", series=_brief(new=("lead",)))

    assert "Introduce yourself as the show's new host." in cue
