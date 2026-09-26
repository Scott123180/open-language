"""T029: plan_session_use is research R-15's reuse/rebuild table as a pure function."""

from app.services.conversation.session import SavedTurn, SessionFingerprint
from app.services.conversation.sync import Rebuild, Reuse, SessionState, plan_session_use
from app.services.llm.selection_types import LLMSelection

_EXPECTED = SessionFingerprint(LLMSelection("ollama", "llama3.2"), "", "digest")

GREETING = SavedTurn("m1", "assistant", "¡Hola! ¿Qué desea?")
ASK = SavedTurn("m2", "user", "Un billete.")
ANSWER = SavedTurn("m3", "assistant", "¿Para dónde?")
YES = SavedTurn("m4", "user", "Sí.")
YES_AGAIN = SavedTurn("m5", "user", "Sí.")


def _live(synced, fingerprint=_EXPECTED, is_broken=False) -> SessionState:
    return SessionState(
        fingerprint=fingerprint,
        synced_turn_ids=tuple(turn.turn_id for turn in synced),
        is_broken=is_broken,
    )


def test_no_live_session_rebuilds_with_the_trailing_learner_turns_pending():
    plan = plan_session_use(None, _EXPECTED, [GREETING, ASK, ANSWER, YES])

    assert plan == Rebuild(synced=(GREETING, ASK, ANSWER), pending=(YES,))


def test_a_different_selection_rebuilds():
    other = SessionFingerprint(LLMSelection("claude", "sonnet"), "low", "digest")

    plan = plan_session_use(
        _live([GREETING, ASK, ANSWER], other), _EXPECTED, [GREETING, ASK, ANSWER, YES]
    )

    assert isinstance(plan, Rebuild)


def test_a_different_effort_rebuilds():
    other = SessionFingerprint(_EXPECTED.selection, "high", "digest")

    assert isinstance(
        plan_session_use(_live([GREETING], other), _EXPECTED, [GREETING, ASK]), Rebuild
    )


def test_a_different_standing_prompt_rebuilds():
    other = SessionFingerprint(_EXPECTED.selection, "", "another digest")

    assert isinstance(
        plan_session_use(_live([GREETING], other), _EXPECTED, [GREETING, ASK]), Rebuild
    )


def test_synced_prefix_with_only_learner_turns_remaining_is_reused():
    plan = plan_session_use(_live([GREETING, ASK, ANSWER]), _EXPECTED, [GREETING, ASK, ANSWER, YES])

    assert plan == Reuse(pending=(YES,))


def test_two_pending_learner_turns_are_reused_in_order():
    history = [GREETING, ASK, ANSWER, YES, YES_AGAIN]

    plan = plan_session_use(_live([GREETING, ASK, ANSWER]), _EXPECTED, history)

    assert plan == Reuse(pending=(YES, YES_AGAIN))


def test_identical_learner_texts_are_told_apart_by_id():
    history = [GREETING, ASK, ANSWER, YES, YES_AGAIN]

    plan = plan_session_use(_live([GREETING, ASK, ANSWER, YES]), _EXPECTED, history)

    assert plan == Reuse(pending=(YES_AGAIN,))


def test_a_remaining_assistant_turn_the_session_did_not_produce_rebuilds():
    plan = plan_session_use(_live([GREETING, ASK]), _EXPECTED, [GREETING, ASK, ANSWER, YES])

    assert plan == Rebuild(synced=(GREETING, ASK, ANSWER), pending=(YES,))


def test_a_deleted_synced_turn_rebuilds():
    plan = plan_session_use(_live([GREETING, ASK, ANSWER]), _EXPECTED, [GREETING, ANSWER, YES])

    assert isinstance(plan, Rebuild)


def test_reordered_turns_rebuild():
    plan = plan_session_use(_live([GREETING, ASK]), _EXPECTED, [ASK, GREETING, YES])

    assert isinstance(plan, Rebuild)


def test_a_broken_session_rebuilds():
    live = _live([GREETING, ASK, ANSWER], is_broken=True)

    assert isinstance(plan_session_use(live, _EXPECTED, [GREETING, ASK, ANSWER, YES]), Rebuild)


def test_an_opening_on_a_matching_session_has_nothing_pending():
    assert plan_session_use(_live([GREETING]), _EXPECTED, [GREETING]) == Reuse(pending=())


def test_an_opening_with_no_session_rebuilds_from_all_of_history():
    assert plan_session_use(None, _EXPECTED, [GREETING]) == Rebuild(synced=(GREETING,), pending=())
