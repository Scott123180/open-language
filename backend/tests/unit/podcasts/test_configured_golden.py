"""011 T026/T056: a configured episode's standing prompts, cues and history, pinned (R5, R19–R22).

The golden file was generated once the configured code existed, then reviewed line by line
against research R5 and the ConfiguredTalk wording:

    backend/.venv/bin/python -m tests.unit.podcasts.test_configured_golden --write

A difference means configured text changed: review it, then regenerate on purpose.
"""

import json
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from app.conversation_levels import ConversationLevel
from app.podcasts.catalog import (
    MAX_REMEMBERED_ABOUT_LEARNER,
    MAX_REMEMBERED_TOPICS,
    PODCAST_FORMATS,
    REMEMBERED_TEXT_BUDGET,
)
from app.podcasts.prompts import (
    CueContext,
    PromptContext,
    ShowBrief,
    build_standing_prompt,
    learner_label_for,
    render_cue,
)
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.cues import episode_history
from app.podcasts.services.episode_settings import EpisodeSettings
from app.podcasts.services.host_talk import ConfiguredTalk
from app.podcasts.services.series_snapshot import RememberedLine, SeriesBrief, SeriesSnapshot
from app.podcasts.services.turn_policy import LEARNER, Ask, LineCue, LineFacts
from app.practice_languages import ConversationLanguages

GOLDEN_FILE = Path(__file__).resolve().parent / "golden" / "configured_prompts.json"
CHARACTERS_PER_TOKEN = 4
STANDING_PROMPT_TOKEN_BUDGET = 1050
"""Measured, not research R5's 900: the same legacy prompt with 010's worst-case series
section already estimates at 867, and the level block is shared text (FR-001)."""
CUE_TOKEN_BUDGET = 60
LEVELS = (ConversationLevel.NATURAL, ConversationLevel.BEGINNER)
HUGO = Host("lead", "Hugo", "curious_interviewer", "es_ES-davefx-medium", "host")
JULIA = Host("second", "Julia", "expert", "es_AR-daniela-high", "co_host")
SHOW = ShowBrief(
    "Big Little Questions",
    "Everyday curiosities, from why toast lands butter-side down onwards.",
    "everyday curiosities",
    "guest",
)
SPANISH = ConversationLanguages.of("es", "en")
PANEL = Cast.for_format(PODCAST_FORMATS["panel"], HUGO, JULIA)
LABEL = "Sam"

Case = tuple[str, Callable[[], str]]


def _talk(subject: str | None = None, covered: str | None = None) -> ConfiguredTalk:
    settings = EpisodeSettings.from_ids(
        style="balanced",
        line_length="medium",
        invite_frequency="sometimes",
        learner_role="guest",
        today_subject=subject,
        covered_personality=covered,
    )
    return ConfiguredTalk(settings)


def _cast_for(format_id: str) -> Cast:
    podcast_format = PODCAST_FORMATS[format_id]
    second = JULIA if podcast_format.host_count == 2 else None
    return Cast.for_format(podcast_format, HUGO, second)


def _standing(format_id: str, level: ConversationLevel, series: SeriesBrief | None = None) -> str:
    cast = _cast_for(format_id)
    label = learner_label_for(PODCAST_FORMATS[format_id], LABEL)
    covered = "expert" if format_id == "one_host" else None
    cues = CueContext(cast, label, _talk(covered=covered), series)
    return build_standing_prompt(PromptContext(SHOW, SPANISH, level, cues))


def _cue(cue: LineCue, subject: str | None = None) -> str:
    return render_cue(cue, CueContext(PANEL, LABEL, _talk(subject)))


CUES = {
    "open|none": (LineCue("lead", "open", Ask.NEVER, False, False), None),
    "open|subject": (LineCue("lead", "open", Ask.NEVER, False, False), "why we yawn"),
    "greet|never": (LineCue("second", "greet", Ask.NEVER, False, False), None),
    "react|allowed": (LineCue("lead", "react", Ask.ALLOWED, False, False), None),
    "react|none-after-pass": (LineCue("lead", "react", Ask.NONE, True, False), None),
    "explain|required": (LineCue("second", "explain", Ask.REQUIRED, False, False), None),
    "explain|required-settle": (LineCue("second", "explain", Ask.REQUIRED, False, True), None),
    "story|none": (LineCue("lead", "story", Ask.NONE, False, False), None),
    "answer|learner": (LineCue("second", "answer", Ask.NONE, False, False, LEARNER), None),
    "answer|host": (LineCue("second", "answer", Ask.ALLOWED, False, False, "lead"), None),
    "answer|both": (LineCue("lead", "answer", Ask.NONE, False, False, LEARNER, True), None),
    "follow_up|allowed": (LineCue("second", "follow_up", Ask.ALLOWED, False, False, LEARNER), None),
    "wrap_up|required": (LineCue("lead", "wrap_up", Ask.REQUIRED, False, False), None),
    "sign_off|none": (LineCue("lead", "sign_off", Ask.NONE, False, False), None),
}
HISTORY_LINES = (
    LineFacts("lead", "open", text="¡Hola a todos!", message_id=1, ask=Ask.NEVER),
    LineFacts("second", "greet", text="Hola, Hugo.", message_id=2, ask=Ask.NEVER, addressee="lead"),
    LineFacts(
        "lead", "react", True, text="¿Y tú, Sam?", message_id=3, ask=Ask.ALLOWED, addressee=LEARNER
    ),
    LineFacts(LEARNER, None, text="Me gusta.", message_id=4),
)


def _history() -> str:
    turns = episode_history(HISTORY_LINES, CueContext(PANEL, LABEL, _talk()))
    return "\n---\n".join(f"{turn.role}: {turn.content}" for turn in turns)


def golden_cases() -> Iterator[Case]:
    for format_id in PODCAST_FORMATS:
        for level in LEVELS:
            yield f"standing|{format_id}|{level.value}", lambda f=format_id, lv=level: _standing(
                f, lv
            )
    for key, (cue, subject) in CUES.items():
        yield f"cue|{key}", lambda c=cue, s=subject: _cue(c, s)
    yield "history|panel", _history


def _full_series() -> SeriesBrief:
    count = MAX_REMEMBERED_TOPICS + MAX_REMEMBERED_ABOUT_LEARNER
    texts = [f"{index:02d}".ljust(REMEMBERED_TEXT_BUDGET // count, "x") for index in range(count)]
    snapshot = SeriesSnapshot(
        9, tuple(texts[:MAX_REMEMBERED_TOPICS]), tuple(texts[MAX_REMEMBERED_TOPICS:])
    )
    return SeriesBrief.of(snapshot, PANEL)


def _golden() -> dict[str, str]:
    return json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))


@pytest.mark.parametrize(("key", "render"), list(golden_cases()), ids=lambda value: str(value))
def test_the_configured_text_equals_the_reviewed_text(key, render):
    assert render() == _golden()[key]


def test_the_golden_file_covers_every_case_and_nothing_else():
    assert set(_golden()) == {key for key, _render in golden_cases()}


@pytest.mark.parametrize("level", LEVELS, ids=lambda level: level.value)
def test_a_configured_prompt_has_the_count_and_no_reply_cap(level):
    prompt = _standing("one_host", level)

    assert "Each host line has three to five sentences" in prompt
    assert "Say at most" not in prompt
    assert "Explains how and why step by step" in prompt
    assert (
        prompt.split("\n\n")[-1 if level is ConversationLevel.NATURAL else -2]
        .split("\n")[-1]
        .startswith("- End every line with who it is for")
    )


def test_a_none_cue_ends_by_saying_not_to_ask():
    assert _cue(CUES["story|none"][0]).endswith("Don't ask Sam anything this time.")


@pytest.mark.parametrize("format_id", list(PODCAST_FORMATS))
def test_a_configured_prompt_with_a_full_series_section_fits_its_budget(format_id):
    prompt = _standing(format_id, ConversationLevel.BEGINNER, _full_series())

    assert len(prompt) / CHARACTERS_PER_TOKEN <= STANDING_PROMPT_TOKEN_BUDGET


@pytest.mark.parametrize("key", list(CUES))
def test_every_configured_cue_fits_its_budget(key):
    cue, subject = CUES[key]

    assert len(_cue(cue, subject)) / CHARACTERS_PER_TOKEN <= CUE_TOKEN_BUDGET


# --- 011 T116/T124: a configured series guest episode (research R10, R11) -----------------

GUEST_FILE = GOLDEN_FILE.parent / "configured_series_guest_prompt.json"
MARCO = Host("second", "Marco", "joker", "es_AR-daniela-high", "co_host")
GUEST_CAST = Cast.for_format(PODCAST_FORMATS["panel"], HUGO, MARCO)
GUEST_SNAPSHOT = SeriesSnapshot(
    6,
    (RememberedLine("las tostadas", ("lead",)), RememberedLine("los bostezos")),
    (RememberedLine("Sam tiene un gato."),),
    guest_slot="second",
    away_host_name="Julia",
)


def _guest_context() -> CueContext:
    return CueContext(GUEST_CAST, LABEL, _talk(), SeriesBrief.of(GUEST_SNAPSHOT, GUEST_CAST))


def guest_cases() -> Iterator[Case]:
    context = _guest_context()
    yield "standing", lambda: build_standing_prompt(
        PromptContext(SHOW, SPANISH, ConversationLevel.BEGINNER, context)
    )
    yield "cue|open", lambda: render_cue(LineCue("lead", "open", Ask.NEVER, False, False), context)
    yield "cue|greet", lambda: render_cue(
        LineCue("second", "greet", Ask.NEVER, False, False), context
    )


def _guest_render(key: str) -> str:
    return dict(guest_cases())[key]()


def test_the_guest_prompt_introduces_the_guest_and_keeps_the_away_host():
    prompt = _guest_render("standing")

    assert "- Marco is today's guest, here for this episode only" in prompt
    assert "- Julia is away today and back next time." in prompt
    assert "las tostadas [Hugo was away for this]" in prompt
    assert "- Hugo only heard about points marked [Hugo was away]" in prompt


def test_the_guest_cues_name_the_guest_and_the_greeting_fits_its_budget():
    """A series opening is 010's recollection plus the subject and the guest, so it is not held
    to the one-off cue budget; the greeting is."""
    opening, greeting = _guest_render("cue|open"), _guest_render("cue|greet")

    assert "Introduce Marco as today's guest, in for Julia, who is away today." in opening
    assert "Greet Hugo and Sam" in greeting
    assert "introduce yourself as today's guest" in greeting
    assert len(greeting) / CHARACTERS_PER_TOKEN <= CUE_TOKEN_BUDGET


def test_the_guest_prompt_fits_its_budget():
    assert len(_guest_render("standing")) / CHARACTERS_PER_TOKEN <= STANDING_PROMPT_TOKEN_BUDGET


@pytest.mark.parametrize(("key", "render"), list(guest_cases()), ids=lambda value: str(value))
def test_the_guest_text_equals_the_reviewed_text(key, render):
    assert render() == json.loads(GUEST_FILE.read_text(encoding="utf-8"))[key]


def _write_golden() -> None:
    GOLDEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    texts = {key: render() for key, render in golden_cases()}
    GOLDEN_FILE.write_text(json.dumps(texts, ensure_ascii=False, indent=1) + "\n", "utf-8")
    guest = {key: render() for key, render in guest_cases()}
    GUEST_FILE.write_text(json.dumps(guest, ensure_ascii=False, indent=1) + "\n", "utf-8")


if __name__ == "__main__" and "--write" in sys.argv:
    _write_golden()
