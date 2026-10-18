"""010 T006: a one-off episode's standing prompt and cues stay byte for byte 007's (FR-007).

The golden file was generated from the 007 code, before any 010 change to `prompts.py`:

    backend/.venv/bin/python -m tests.unit.podcasts.test_one_off_golden --write

It is never regenerated: a difference means the one-off text changed. The explicit
`series=None` case lives in `test_series_prompts.py`.
"""

import itertools
import json
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from app.conversation_levels import ConversationLevel
from app.podcasts.catalog import PODCAST_FORMATS
from app.podcasts.prompts import ShowBrief, build_standing_prompt, learner_label_for, render_cue
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.turn_policy import LineCue
from app.practice_languages import ConversationLanguages

GOLDEN_FILE = Path(__file__).resolve().parent / "golden" / "one_off_prompts.json"
LEARNER_NAMES = ("Sam", None)
LEVELS = (ConversationLevel.NATURAL, ConversationLevel.BEGINNER)
INTENTS = ("open", "greet", "discuss", "wrap_up", "sign_off")
LABELS = ("Sam", "our guest", "our listeners")
LUCIA = Host("lead", "Lucía", "enthusiast", "es_AR-daniela-high", "host", "Loves markets.")
MARCO = Host("second", "Marco", "dry_sceptic", "es_ES-davefx-medium", "co_host")
SHOW = ShowBrief(
    title="Weekend Food Talk",
    premise="Two food lovers swap weekend cooking wins and disasters.",
    topic="food",
    learner_role="guest",
)
SPANISH = ConversationLanguages.of("es", "en")
PANEL_CAST = Cast.for_format(PODCAST_FORMATS["panel"], LUCIA, MARCO)

Case = tuple[str, Callable[[], str]]


def _cast_for(format_id: str) -> Cast:
    podcast_format = PODCAST_FORMATS[format_id]
    second = MARCO if podcast_format.host_count == 2 else None
    return Cast.for_format(podcast_format, LUCIA, second)


def _standing_case(format_id: str, name: str | None, level: ConversationLevel) -> Case:
    label = learner_label_for(PODCAST_FORMATS[format_id], name)
    key = f"standing|{format_id}|{name}|{level.value}"
    return key, lambda: build_standing_prompt(SHOW, _cast_for(format_id), label, SPANISH, level)


def _cue_case(intent: str, invites: bool, after_pass: bool, settle: bool, label: str) -> Case:
    speaker = "second" if intent == "greet" else "lead"
    cue = LineCue(speaker, intent, invites, after_pass, settle)
    key = f"cue|{intent}|{invites}|{after_pass}|{settle}|{label}"
    return key, lambda: render_cue(cue, PANEL_CAST, label)


def golden_cases() -> Iterator[Case]:
    for format_id, name, level in itertools.product(PODCAST_FORMATS, LEARNER_NAMES, LEVELS):
        yield _standing_case(format_id, name, level)
    flags = itertools.product((False, True), repeat=3)
    for intent, (invites, after_pass, settle), label in itertools.product(INTENTS, flags, LABELS):
        if settle and not invites:
            continue
        yield _cue_case(intent, invites, after_pass, settle, label)


def _golden() -> dict[str, str]:
    return json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))


@pytest.mark.parametrize(("key", "render"), list(golden_cases()), ids=lambda value: str(value))
def test_the_one_off_text_equals_the_007_text(key, render):
    assert render() == _golden()[key]


def test_the_golden_file_covers_every_case_and_nothing_else():
    assert set(_golden()) == {key for key, _render in golden_cases()}


def _write_golden() -> None:
    GOLDEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    texts = {key: render() for key, render in golden_cases()}
    GOLDEN_FILE.write_text(json.dumps(texts, ensure_ascii=False, indent=1) + "\n", "utf-8")


if __name__ == "__main__" and "--write" in sys.argv:
    _write_golden()
