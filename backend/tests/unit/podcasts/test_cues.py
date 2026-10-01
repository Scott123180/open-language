"""T017: the saved history of an episode, with its producer cues re-rendered (research R3)."""

from app.podcasts.catalog import PODCAST_FORMATS
from app.podcasts.prompts import render_cue
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.cues import episode_history, next_turn_history, stored_cue
from app.podcasts.services.turn_policy import LEARNER, LineCue, LineFacts
from app.services.conversation import SavedTurn, SessionKey, SessionKind, TurnRequest

PANEL = PODCAST_FORMATS["panel"]
LUCIA = Host("lead", "Lucía", "enthusiast", "es_AR-daniela-high", "host")
MARCO = Host("second", "Marco", "dry_sceptic", "es_ES-davefx-medium", "co_host")
CAST = Cast.for_format(PANEL, LUCIA, MARCO)
LABEL = "Sam"

LINES = (
    LineFacts("lead", "open", False, False, "¡Bienvenidos!", message_id=11),
    LineFacts("second", "greet", True, True, "Hola, soy Marco.", message_id=12),
    LineFacts("lead", "discuss", True, False, "¿Tú qué opinas, Sam?", message_id=13),
    LineFacts(LEARNER, None, False, False, "Me encanta la paella.", message_id=14),
)


def test_host_lines_are_assistant_turns_after_their_cue():
    history = episode_history(LINES, CAST, LABEL)

    assert [(turn.turn_id, turn.role) for turn in history] == [
        ("c0", "user"),
        ("p11", "assistant"),
        ("c1", "user"),
        ("p12", "assistant"),
        ("c2", "user"),
        ("p13", "assistant"),
        ("p14", "user"),
    ]


def test_a_host_line_keeps_its_stored_text():
    history = episode_history(LINES, CAST, LABEL)

    assert history[1].content == "¡Bienvenidos!"


def test_a_learner_line_is_labelled_with_the_learner_label():
    assert episode_history(LINES, CAST, LABEL)[-1].content == "Sam: Me encanta la paella."


def test_each_cue_is_rendered_from_the_stored_facts():
    history = episode_history(LINES, CAST, LABEL)

    assert history[0].content == render_cue(stored_cue(LINES, 0), CAST, LABEL)
    assert history[4].content == render_cue(stored_cue(LINES, 2), CAST, LABEL)


def test_a_stored_cue_remembers_the_pass_before_it():
    assert stored_cue(LINES, 2) == LineCue(
        speaker_slot="lead",
        intent="discuss",
        invites_learner=True,
        is_after_pass=True,
        is_settle_invite=True,
    )


def test_re_rendering_the_history_is_byte_for_byte_identical():
    assert episode_history(LINES, CAST, LABEL) == episode_history(tuple(LINES), CAST, LABEL)


def test_the_next_turn_ends_with_a_fresh_cue_after_every_line():
    cue = LineCue("second", "discuss", True, False, False)

    history = next_turn_history(LINES, CAST, LABEL, cue)

    assert history[:-1] == episode_history(LINES, CAST, LABEL)
    assert history[-1] == SavedTurn("c4", "user", render_cue(cue, CAST, LABEL))


def test_the_engine_accepts_the_next_turn():
    cue = LineCue("lead", "open", False, False, False)

    request = TurnRequest(
        key=SessionKey(SessionKind.PODCAST, "57"),
        standing_prompt="prompt",
        history=next_turn_history((), CAST, LABEL, cue),
        guidance=None,
        opening_instruction=None,
    )

    assert [turn.turn_id for turn in request.history] == ["c0"]
