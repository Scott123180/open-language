"""Integration tests for the correction wiring on POST /api/chat/{id}/message."""

from app.corrections.services.evaluator import CorrectionFinding
from app.corrections.services.storage import FeedbackDraft
from app.corrections.services.strategies import TurnPlan
from app.main import app
from tests.integration.corrections.conftest import (
    StubStrategy,
    build_gentle_harness,
    build_strict_harness,
)

_CORRECTION = FeedbackDraft(
    kind="correction",
    category="conjugation",
    error_fragment="Yo tener",
    corrected_text="Yo tengo veinte años",
    explanation="Tener must be conjugated as tengo with yo.",
    mode="strict",
    rank=0,
)


def _kinds(events: list[dict]) -> list[str]:
    """The frame sequence, as a comparable list of frame names."""
    sequence = []
    for event in events:
        if "token" in event:
            sequence.append("token")
        elif event.get("done"):
            sequence.append("done")
        elif "error" in event:
            sequence.append("error")
        else:
            sequence.append(event["event"])
    return sequence


class TestOffModeIsUnchanged:
    """SC-002: Off mode's stream is byte-identical to the pre-feature stream."""

    def test_emits_the_pre_feature_frame_sequence(self, make_harness) -> None:
        harness = make_harness(mode="off")
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        assert _kinds(events) == ["user_message_saved", "token", "token", "done"]

    def test_emits_no_feedback_frame(self, make_harness) -> None:
        harness = make_harness(mode="off")
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        assert all(e.get("event") != "feedback" for e in events)

    def test_makes_exactly_one_llm_call(self, make_harness) -> None:
        harness = make_harness(mode="off")
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tener veinte años")

        assert len(harness.llm.stream_calls) == 1

    def test_done_carries_a_real_assistant_message_id(self, make_harness) -> None:
        harness = make_harness(mode="off")
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        assistant = harness.storage.get_message(events[-1]["message_id"])
        assert assistant is not None
        assert assistant.role == "assistant"

    def test_writes_no_correction_rows(self, make_harness) -> None:
        harness = make_harness(mode="off")
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tener veinte años")

        assert harness.correction_storage.list_feedback(conv_id) == []


class TestFeedbackFrameWiring:
    """T030a: driven by stub strategies, so the wiring is testable on its own."""

    def test_feedback_frame_is_emitted_once(self, make_harness) -> None:
        strategy = StubStrategy(
            TurnPlan((_CORRECTION,), generate_reply=True, reply_prompt_suffix=None)
        )
        harness = make_harness(mode="strict", strategy=strategy)
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        assert _kinds(events).count("feedback") == 1

    def test_feedback_frame_sits_between_user_message_saved_and_the_first_token(
        self, make_harness
    ) -> None:
        strategy = StubStrategy(
            TurnPlan((_CORRECTION,), generate_reply=True, reply_prompt_suffix=None)
        )
        harness = make_harness(mode="strict", strategy=strategy)
        conv_id = harness.create_conversation()

        sequence = _kinds(harness.send(conv_id, "Yo tener veinte años"))

        assert sequence.index("feedback") == 1
        assert sequence.index("feedback") < sequence.index("token")

    def test_feedback_frame_carries_the_learner_message_id_and_notes(self, make_harness) -> None:
        strategy = StubStrategy(
            TurnPlan((_CORRECTION,), generate_reply=True, reply_prompt_suffix=None)
        )
        harness = make_harness(mode="strict", strategy=strategy)
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        user_saved = events[0]
        feedback = next(e for e in events if e.get("event") == "feedback")
        assert feedback["message_id"] == user_saved["message_id"]
        assert len(feedback["notes"]) == 1
        assert feedback["notes"][0]["corrected_text"] == "Yo tengo veinte años"
        assert feedback["notes"][0]["kind"] == "correction"

    def test_notes_are_persisted(self, make_harness) -> None:
        strategy = StubStrategy(
            TurnPlan((_CORRECTION,), generate_reply=True, reply_prompt_suffix=None)
        )
        harness = make_harness(mode="strict", strategy=strategy)
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tener veinte años")

        stored = harness.correction_storage.list_feedback(conv_id)
        assert len(stored) == 1
        assert stored[0].explanation == _CORRECTION.explanation

    def test_no_reply_plan_streams_zero_tokens(self, make_harness) -> None:
        strategy = StubStrategy(
            TurnPlan((_CORRECTION,), generate_reply=False, reply_prompt_suffix=None)
        )
        harness = make_harness(mode="strict", strategy=strategy)
        conv_id = harness.create_conversation()

        sequence = _kinds(harness.send(conv_id, "Yo tener veinte años"))

        assert "token" not in sequence

    def test_no_reply_plan_writes_no_assistant_row(self, make_harness) -> None:
        strategy = StubStrategy(
            TurnPlan((_CORRECTION,), generate_reply=False, reply_prompt_suffix=None)
        )
        harness = make_harness(mode="strict", strategy=strategy)
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tener veinte años")

        roles = [m.role for m in harness.storage.get_messages(conv_id)]
        assert roles == ["user"]

    def test_no_reply_plan_makes_no_llm_call(self, make_harness) -> None:
        strategy = StubStrategy(
            TurnPlan((_CORRECTION,), generate_reply=False, reply_prompt_suffix=None)
        )
        harness = make_harness(mode="strict", strategy=strategy)
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tener veinte años")

        assert harness.llm.stream_calls == []

    def test_no_reply_plan_ends_with_a_null_message_id(self, make_harness) -> None:
        strategy = StubStrategy(
            TurnPlan((_CORRECTION,), generate_reply=False, reply_prompt_suffix=None)
        )
        harness = make_harness(mode="strict", strategy=strategy)
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        assert events[-1] == {"done": True, "message_id": None}

    def test_reply_prompt_suffix_is_appended_to_the_system_prompt(self, make_harness) -> None:
        suffix = "Work the corrected form into your reply."
        strategy = StubStrategy(TurnPlan((), generate_reply=True, reply_prompt_suffix=suffix))
        harness = make_harness(mode="gentle", strategy=strategy)
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tener veinte años")

        system_prompt = harness.llm.stream_calls[0][0].content
        assert system_prompt.endswith(suffix)

    def test_reply_prompt_suffix_does_not_displace_the_critical_language_rule(
        self, make_harness
    ) -> None:
        suffix = "Work the corrected form into your reply."
        strategy = StubStrategy(TurnPlan((), generate_reply=True, reply_prompt_suffix=suffix))
        harness = make_harness(mode="gentle", strategy=strategy)
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tener veinte años")

        system_prompt = harness.llm.stream_calls[0][0].content
        assert system_prompt.startswith("CRITICAL LANGUAGE RULE")

    def test_an_empty_plan_leaves_the_stream_untouched(self, make_harness) -> None:
        strategy = StubStrategy(TurnPlan((), generate_reply=True, reply_prompt_suffix=None))
        harness = make_harness(mode="strict", strategy=strategy)
        conv_id = harness.create_conversation()

        sequence = _kinds(harness.send(conv_id, "Yo tener veinte años"))

        assert sequence == ["user_message_saved", "token", "token", "done"]

    def test_the_strategy_receives_the_conversation_context(self, make_harness) -> None:
        strategy = StubStrategy(TurnPlan((), generate_reply=True, reply_prompt_suffix=None))
        harness = make_harness(mode="strict", strategy=strategy)
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tener veinte años")

        context = strategy.contexts[0]
        assert context.conversation_id == conv_id
        assert context.learner_text == "Yo tener veinte años"
        assert context.target_language == "Spanish"
        assert context.native_language == "English"


class TestGentleNotesAreNotStreamed:
    """A gentle correction is persisted but never rendered as a note (§2.3)."""

    def test_gentle_feedback_emits_no_frame(self, make_harness) -> None:
        gentle_note = FeedbackDraft(
            kind="correction",
            category="conjugation",
            error_fragment="Yo tener",
            corrected_text="Yo tengo veinte años",
            explanation="Conjugate tener as tengo.",
            mode="gentle",
            rank=0,
        )
        strategy = StubStrategy(
            TurnPlan((gentle_note,), generate_reply=True, reply_prompt_suffix=None)
        )
        harness = make_harness(mode="gentle", strategy=strategy)
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        assert all(e.get("event") != "feedback" for e in events)
        assert len(harness.correction_storage.list_feedback(conv_id)) == 1


def _finding(rank: int = 0, fragment: str = "Yo tener") -> CorrectionFinding:
    return CorrectionFinding(
        category="conjugation",
        error_fragment=fragment,
        corrected_text="Yo tengo veinte años",
        explanation="Tener must be conjugated as tengo with yo.",
        rank=rank,
    )


class TestStrictModeFlaggedTurn:
    """US1: the correction is the turn's only output (FR-016, FR-020, SC-005)."""

    def test_emits_feedback_then_a_null_done(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        assert _kinds(events) == ["user_message_saved", "feedback", "done"]
        assert events[-1]["message_id"] is None

    def test_streams_no_tokens(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        assert all("token" not in e for e in events)

    def test_stores_no_assistant_message_row(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tener veinte años")

        assert [m.role for m in harness.storage.get_messages(conv_id)] == ["user"]

    def test_the_frame_reports_the_conversation_as_awaiting_a_retry(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        feedback = next(e for e in events if e.get("event") == "feedback")
        assert feedback["awaiting_retry"] is True

    def test_the_correction_text_never_enters_a_message_row(self, make_harness) -> None:
        """FR-020: feedback lives outside messages.content, so TTS cannot reach it."""
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tener veinte años")

        contents = [m.content for m in harness.storage.get_messages(conv_id)]
        assert all("Yo tengo veinte años" not in c for c in contents)

    def test_a_clean_message_gets_an_ordinary_reply(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, ())
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tengo veinte años")

        assert _kinds(events) == ["user_message_saved", "token", "token", "done"]


class TestStrictRetryKeepsTheHistory:
    """FR-017: the retry is answered with the full prior history intact."""

    def test_the_message_after_a_correction_gets_a_reply(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()
        harness.send(conv_id, "Yo tener veinte años")

        harness.evaluator.findings = ()
        events = harness.send(conv_id, "Yo tengo veinte años")

        assert any("token" in e for e in events)

    def test_the_reply_is_built_from_the_whole_transcript(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()
        harness.send(conv_id, "Yo tener veinte años")

        harness.evaluator.findings = ()
        harness.send(conv_id, "Yo tengo veinte años")

        sent_messages = harness.llm.stream_calls[0]
        learner_lines = [m.content for m in sent_messages if m.role == "user"]
        assert learner_lines == ["Yo tener veinte años", "Yo tengo veinte años"]

    def test_the_corrected_attempt_is_still_in_the_transcript(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()
        harness.send(conv_id, "Yo tener veinte años")

        harness.evaluator.findings = ()
        harness.send(conv_id, "Yo tengo veinte años")

        contents = [m.content for m in harness.storage.get_messages(conv_id)]
        assert "Yo tener veinte años" in contents


class TestStrictNeverTrapsTheLearner:
    """FR-018 / SC-006: the third consecutive attempt is answered regardless."""

    def test_the_third_attempt_is_answered_even_with_a_new_error(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        first = harness.send(conv_id, "Yo tener veinte años")
        second = harness.send(conv_id, "Yo tenes veinte años")
        third = harness.send(conv_id, "Yo tenir veinte años")

        assert _kinds(first) == ["user_message_saved", "feedback", "done"]
        assert _kinds(second) == ["user_message_saved", "feedback", "done"]
        assert any("token" in e for e in third)

    def test_the_counter_resets_after_the_cap_is_released(self, make_harness) -> None:
        """The pause starts over, so the learner is corrected again from here."""
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()
        harness.send(conv_id, "one error")
        harness.send(conv_id, "two error")

        harness.send(conv_id, "three error")

        state = harness.correction_storage.get_pause_state(conv_id)
        assert state.consecutive_corrected_attempts == 0
        assert state.awaiting_retry is False


class TestGentleMode:
    """US2: the correction is woven into the reply and nothing stops (FR-012, FR-013)."""

    def test_streams_the_reply_tokens(self, make_harness) -> None:
        harness = build_gentle_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        assert _kinds(events) == ["user_message_saved", "token", "token", "done"]

    def test_emits_no_feedback_frame(self, make_harness) -> None:
        harness = build_gentle_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        assert all(e.get("event") != "feedback" for e in events)

    def test_persists_the_correction_with_the_gentle_mode(self, make_harness) -> None:
        harness = build_gentle_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tener veinte años")

        stored = harness.correction_storage.list_feedback(conv_id)
        assert len(stored) == 1
        assert stored[0].mode == "gentle"

    def test_leaves_the_pause_counter_untouched(self, make_harness) -> None:
        harness = build_gentle_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tener veinte años")

        state = harness.correction_storage.get_pause_state(conv_id)
        assert state.consecutive_corrected_attempts == 0
        assert state.awaiting_retry is False

    def test_the_recast_instruction_reaches_the_system_prompt(self, make_harness) -> None:
        harness = build_gentle_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tener veinte años")

        system_prompt = harness.llm.stream_calls[0][0].content
        assert "Yo tengo veinte años" in system_prompt
        assert system_prompt.startswith("CRITICAL LANGUAGE RULE")

    def test_a_clean_message_leaves_the_prompt_alone(self, make_harness) -> None:
        harness = build_gentle_harness(make_harness, ())
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tengo veinte años")

        system_prompt = harness.llm.stream_calls[0][0].content
        assert "corrected form" not in system_prompt
        assert harness.correction_storage.list_feedback(conv_id) == []

    def test_the_gentle_note_is_never_replayed_to_the_client(self, make_harness) -> None:
        harness = build_gentle_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()
        harness.send(conv_id, "Yo tener veinte años")

        body = harness.client.get(f"/api/corrections/conversations/{conv_id}").json()

        assert body["feedback"] == []


class TestLowConfidenceMessages:
    """FR-010a, FR-027, FR-028 over the wire."""

    def test_strict_asks_the_learner_to_repeat(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        events = harness.send(
            conv_id, "Yo tener veinte años", input_source="voice", transcription_confidence=0.2
        )

        feedback = next(e for e in events if e.get("event") == "feedback")
        assert [n["kind"] for n in feedback["notes"]] == ["repeat_request"]

    def test_strict_produces_no_correction_and_no_reply(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        events = harness.send(
            conv_id, "Yo tener veinte años", input_source="voice", transcription_confidence=0.2
        )

        assert _kinds(events) == ["user_message_saved", "feedback", "done"]
        assert events[-1]["message_id"] is None
        stored = harness.correction_storage.list_feedback(conv_id)
        assert all(r.kind != "correction" for r in stored)

    def test_gentle_replies_normally_without_correcting(self, make_harness) -> None:
        harness = build_gentle_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        events = harness.send(
            conv_id, "Yo tener veinte años", input_source="voice", transcription_confidence=0.2
        )

        assert _kinds(events) == ["user_message_saved", "token", "token", "done"]
        assert harness.correction_storage.list_feedback(conv_id) == []

    def test_gentle_never_pauses_on_a_low_confidence_message(self, make_harness) -> None:
        harness = build_gentle_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        harness.send(
            conv_id, "Yo tener veinte años", input_source="voice", transcription_confidence=0.2
        )

        assert harness.correction_storage.get_pause_state(conv_id).awaiting_retry is False

    def test_a_zero_confidence_message_is_treated_as_low(self, make_harness) -> None:
        """Hallucination-on-silence: text present, every segment silent."""
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        events = harness.send(
            conv_id, "Thank you for watching", input_source="voice", transcription_confidence=0.0
        )

        feedback = next(e for e in events if e.get("event") == "feedback")
        assert feedback["notes"][0]["kind"] == "repeat_request"

    def test_an_omitted_confidence_is_evaluated_normally(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        feedback = next(e for e in events if e.get("event") == "feedback")
        assert feedback["notes"][0]["kind"] == "correction"

    def test_a_second_low_confidence_message_proceeds_normally(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, ())
        conv_id = harness.create_conversation()
        harness.send(conv_id, "mumble", input_source="voice", transcription_confidence=0.1)

        events = harness.send(
            conv_id, "mumble again", input_source="voice", transcription_confidence=0.1
        )

        assert _kinds(events) == ["user_message_saved", "token", "token", "done"]

    def test_the_confidence_is_persisted_on_the_message(self, make_harness) -> None:
        harness = build_gentle_harness(make_harness, ())
        conv_id = harness.create_conversation()

        harness.send(
            conv_id, "Yo tengo veinte años", input_source="voice", transcription_confidence=0.42
        )

        learner = [m for m in harness.storage.get_messages(conv_id) if m.role == "user"][0]
        assert learner.transcription_confidence == 0.42
        assert learner.is_low_confidence is True


class TestConfidenceRequestContract:
    """quickstart 5.14, 5.15."""

    def test_a_confidence_above_one_is_rejected(self, make_harness) -> None:
        harness = make_harness(mode="off")
        conv_id = harness.create_conversation()

        response = harness.post_message(
            conv_id, "Hola", input_source="voice", transcription_confidence=1.5
        )

        assert response.status_code == 422

    def test_a_negative_confidence_is_rejected(self, make_harness) -> None:
        harness = make_harness(mode="off")
        conv_id = harness.create_conversation()

        response = harness.post_message(
            conv_id, "Hola", input_source="voice", transcription_confidence=-0.1
        )

        assert response.status_code == 422

    def test_a_keyboard_message_persists_no_confidence(self, make_harness) -> None:
        harness = build_gentle_harness(make_harness, ())
        conv_id = harness.create_conversation()

        harness.send(
            conv_id, "Yo tengo veinte años", input_source="keyboard", transcription_confidence=0.1
        )

        learner = [m for m in harness.storage.get_messages(conv_id) if m.role == "user"][0]
        assert learner.transcription_confidence is None
        assert learner.is_low_confidence is None

    def test_a_keyboard_message_is_still_evaluated(self, make_harness) -> None:
        """A client-supplied confidence must not silence corrections on typed input."""
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        events = harness.send(
            conv_id, "Yo tener veinte años", input_source="keyboard", transcription_confidence=0.0
        )

        feedback = next(e for e in events if e.get("event") == "feedback")
        assert feedback["notes"][0]["kind"] == "correction"


class TestRestraint:
    """FR-007, FR-008, FR-009: correct what confuses, never more than two, never praise."""

    def test_four_findings_surface_at_most_two(self, make_harness) -> None:
        from app.corrections.config import MAX_CORRECTIONS_PER_MESSAGE

        four = tuple(_finding(rank=i, fragment=f"e{i}") for i in range(4))
        harness = build_strict_harness(make_harness, four)
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "una frase con cuatro errores graves")

        feedback = next(e for e in events if e.get("event") == "feedback")
        assert len(feedback["notes"]) <= MAX_CORRECTIONS_PER_MESSAGE

    def test_the_surfaced_corrections_are_ordered_by_rank(self, make_harness) -> None:
        four = tuple(_finding(rank=i, fragment=f"e{i}") for i in range(4))
        harness = build_strict_harness(make_harness, four)
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "una frase con cuatro errores graves")

        feedback = next(e for e in events if e.get("event") == "feedback")
        assert [n["rank"] for n in feedback["notes"]] == [0, 1]

    def test_a_sentence_the_evaluator_clears_surfaces_nothing(self, make_harness) -> None:
        """A missing diacritic is ruled out in the prompt, so no finding comes back."""
        harness = build_strict_harness(make_harness, ())
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tengo veinte anos")

        assert all(e.get("event") != "feedback" for e in events)

    def test_a_correct_sentence_produces_no_praise(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, ())
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tengo veinte años")

        assert harness.correction_storage.list_feedback(conv_id) == []


# The SC-003 fixed sentence set: ten with a deliberate substantive error, ten correct.
SENTENCES_WITH_AN_ERROR = [
    "Yo tener veinte años",
    "Ella son mi hermana",
    "Nosotros va al mercado mañana",
    "El agua está fría y el leche caliente",
    "Yo gusta mucho el café",
    "Ayer yo voy al cine con mis amigos",
    "La casa es muy grande y bonito",
    "Tú tienes que estudiar más para el examen difícil son",
    "Yo he comido ya el desayuno antes de que yo salgo",
    "Quiero que tú vienes conmigo a la fiesta",
]

CORRECT_SENTENCES = [
    "Yo tengo veinte años",
    "Ella es mi hermana",
    "Nosotros vamos al mercado mañana",
    "El agua está fría y la leche caliente",
    "A mí me gusta mucho el café",
    "Ayer fui al cine con mis amigos",
    "La casa es muy grande y bonita",
    "Tienes que estudiar más para el examen difícil",
    "Ya he desayunado antes de salir",
    "Quiero que vengas conmigo a la fiesta",
]


class TestDetectionPipeline:
    """T074: a determinism test of the wiring. NOT the SC-003 benchmark (that is T074a)."""

    def test_every_reported_finding_reaches_the_learner(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()

        surfaced = 0
        for sentence in SENTENCES_WITH_AN_ERROR:
            harness.evaluator.findings = (_finding(),)
            events = harness.send(conv_id, sentence)
            if any(e.get("event") == "feedback" for e in events):
                surfaced += 1
            # Clear the pause so the next sentence is evaluated rather than capped.
            harness.correction_storage.set_pause_state(conv_id, 0, awaiting_clarification=False)

        assert surfaced == len(SENTENCES_WITH_AN_ERROR)

    def test_clean_sentences_surface_nothing(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, ())
        conv_id = harness.create_conversation()

        for sentence in CORRECT_SENTENCES:
            events = harness.send(conv_id, sentence)
            assert all(e.get("event") != "feedback" for e in events)


class TestChangingTheModeMidConversation:
    """FR-004: a mode change applies from the learner's next message only."""

    def test_existing_feedback_rows_are_left_byte_identical(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()
        harness.send(conv_id, "Yo tener veinte años")
        before = harness.correction_storage.list_feedback(conv_id)

        # The learner switches to Off; the strategy for the next turn is the null one.
        from app.corrections.services.strategies import OffCorrectionStrategy
        from app.services.factory import get_correction_strategy

        app.dependency_overrides[get_correction_strategy] = lambda: OffCorrectionStrategy()
        harness.send(conv_id, "Yo tener veinte años otra vez")

        assert harness.correction_storage.list_feedback(conv_id) == before

    def test_switching_to_off_answers_the_next_message_normally(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()
        harness.send(conv_id, "Yo tener veinte años")
        assert harness.correction_storage.get_pause_state(conv_id).awaiting_retry is True

        from app.corrections.services.strategies import OffCorrectionStrategy
        from app.services.factory import get_correction_strategy

        app.dependency_overrides[get_correction_strategy] = lambda: OffCorrectionStrategy()
        events = harness.send(conv_id, "Yo tener veinte años otra vez")

        assert _kinds(events) == ["user_message_saved", "token", "token", "done"]

    def test_an_open_pause_is_inert_while_the_mode_is_off(self, make_harness) -> None:
        """Off reads neither correction table, so the stored pause changes nothing."""
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()
        harness.send(conv_id, "Yo tener veinte años")

        from app.corrections.services.strategies import OffCorrectionStrategy
        from app.services.factory import get_correction_strategy

        app.dependency_overrides[get_correction_strategy] = lambda: OffCorrectionStrategy()
        harness.send(conv_id, "Yo tener veinte años otra vez")

        state = harness.correction_storage.get_pause_state(conv_id)
        assert state.consecutive_corrected_attempts == 1
