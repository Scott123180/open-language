"""Integration tests for GET /api/corrections/conversations/{id} (contracts §1.5)."""

from app.corrections.services.evaluator import CorrectionFinding
from app.corrections.services.storage import FeedbackDraft
from tests.integration.corrections.conftest import build_strict_harness


def _correction(mode: str = "strict", rank: int = 0, fragment: str = "Yo tener") -> FeedbackDraft:
    return FeedbackDraft(
        kind="correction",
        category="conjugation",
        error_fragment=fragment,
        corrected_text="Yo tengo veinte años",
        explanation="Tener must be conjugated as tengo with yo.",
        mode=mode,
        rank=rank,
    )


def _repeat_request() -> FeedbackDraft:
    return FeedbackDraft(
        kind="repeat_request",
        category=None,
        error_fragment=None,
        corrected_text=None,
        explanation="I didn't quite catch that — could you say it again?",
        mode="strict",
        rank=0,
    )


def _seed_user_message(harness, conversation_id: int, content: str = "Yo tener veinte años") -> int:
    return harness.storage.save_message(
        conversation_id=conversation_id, role="user", content=content, input_source="keyboard"
    ).id


class TestReplay:
    def test_returns_zeroed_state_for_an_uncorrected_conversation(self, make_harness) -> None:
        harness = make_harness(mode="off")
        conv_id = harness.create_conversation()

        body = harness.client.get(f"/api/corrections/conversations/{conv_id}").json()

        assert body == {
            "conversation_id": conv_id,
            "awaiting_retry": False,
            "awaiting_clarification": False,
            "consecutive_corrected_attempts": 0,
            "feedback": [],
        }

    def test_returns_404_for_an_unknown_conversation(self, make_harness) -> None:
        harness = make_harness(mode="off")

        response = harness.client.get("/api/corrections/conversations/4242")

        assert response.status_code == 404
        assert response.json()["detail"] == "Conversation not found"

    def test_returns_stored_corrections(self, make_harness) -> None:
        harness = make_harness(mode="strict")
        conv_id = harness.create_conversation()
        msg_id = _seed_user_message(harness, conv_id)
        harness.correction_storage.save_feedback(msg_id, [_correction()])

        body = harness.client.get(f"/api/corrections/conversations/{conv_id}").json()

        assert len(body["feedback"]) == 1
        note = body["feedback"][0]
        assert note["message_id"] == msg_id
        assert note["kind"] == "correction"
        assert note["corrected_text"] == "Yo tengo veinte años"
        assert note["mode"] == "strict"

    def test_orders_by_message_then_rank(self, make_harness) -> None:
        harness = make_harness(mode="strict")
        conv_id = harness.create_conversation()
        first = _seed_user_message(harness, conv_id, "one")
        second = _seed_user_message(harness, conv_id, "two")
        harness.correction_storage.save_feedback(
            second, [_correction(rank=1, fragment="b"), _correction(rank=0, fragment="a")]
        )
        harness.correction_storage.save_feedback(first, [_correction(rank=0, fragment="z")])

        body = harness.client.get(f"/api/corrections/conversations/{conv_id}").json()

        assert [(n["message_id"], n["rank"]) for n in body["feedback"]] == [
            (first, 0),
            (second, 0),
            (second, 1),
        ]

    def test_excludes_gentle_corrections(self, make_harness) -> None:
        harness = make_harness(mode="gentle")
        conv_id = harness.create_conversation()
        msg_id = _seed_user_message(harness, conv_id)
        harness.correction_storage.save_feedback(msg_id, [_correction(mode="gentle")])

        body = harness.client.get(f"/api/corrections/conversations/{conv_id}").json()

        assert body["feedback"] == []

    def test_includes_repeat_requests(self, make_harness) -> None:
        harness = make_harness(mode="strict")
        conv_id = harness.create_conversation()
        msg_id = _seed_user_message(harness, conv_id)
        harness.correction_storage.save_feedback(msg_id, [_repeat_request()])

        body = harness.client.get(f"/api/corrections/conversations/{conv_id}").json()

        assert len(body["feedback"]) == 1
        assert body["feedback"][0]["kind"] == "repeat_request"
        assert body["feedback"][0]["category"] is None

    def test_reports_the_stored_pause_counters(self, make_harness) -> None:
        harness = make_harness(mode="strict")
        conv_id = harness.create_conversation()
        _seed_user_message(harness, conv_id)
        harness.correction_storage.set_pause_state(conv_id, 1, awaiting_clarification=False)

        body = harness.client.get(f"/api/corrections/conversations/{conv_id}").json()

        assert body["consecutive_corrected_attempts"] == 1
        assert body["awaiting_retry"] is True


def _finding() -> CorrectionFinding:
    return CorrectionFinding(
        category="conjugation",
        error_fragment="Yo tener",
        corrected_text="Yo tengo veinte años",
        explanation="Tener must be conjugated as tengo with yo.",
        rank=0,
    )


class TestPauseSurvivesReopening:
    """FR-022 and FR-029: reopening restores both the notes and the open pause."""

    def test_a_conversation_reopened_mid_pause_still_awaits_a_retry(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()
        harness.send(conv_id, "Yo tener veinte años")

        body = harness.client.get(f"/api/corrections/conversations/{conv_id}").json()

        assert body["awaiting_retry"] is True
        assert body["consecutive_corrected_attempts"] == 1

    def test_previously_issued_corrections_are_still_returned(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()
        harness.send(conv_id, "Yo tener veinte años")

        body = harness.client.get(f"/api/corrections/conversations/{conv_id}").json()

        assert len(body["feedback"]) == 1
        assert body["feedback"][0]["corrected_text"] == "Yo tengo veinte años"

    def test_the_pause_clears_once_the_retry_is_answered(self, make_harness) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()
        harness.send(conv_id, "Yo tener veinte años")

        harness.evaluator.findings = ()
        harness.send(conv_id, "Yo tengo veinte años")
        body = harness.client.get(f"/api/corrections/conversations/{conv_id}").json()

        assert body["awaiting_retry"] is False
        assert body["consecutive_corrected_attempts"] == 0

    def test_corrections_from_earlier_turns_remain_after_the_pause_clears(
        self, make_harness
    ) -> None:
        harness = build_strict_harness(make_harness, (_finding(),))
        conv_id = harness.create_conversation()
        harness.send(conv_id, "Yo tener veinte años")

        harness.evaluator.findings = ()
        harness.send(conv_id, "Yo tengo veinte años")
        body = harness.client.get(f"/api/corrections/conversations/{conv_id}").json()

        assert len(body["feedback"]) == 1


class TestOnDemandLearningToolsAreUnaffected:
    """FR-024, FR-025: automatic correction neither pre-fills nor suppresses them."""

    def _seed_corrected_and_clean_messages(self, harness, conv_id: int) -> tuple[int, int]:
        corrected = harness.storage.save_message(
            conversation_id=conv_id,
            role="user",
            content="Yo tener veinte años",
            input_source="keyboard",
        ).id
        clean = harness.storage.save_message(
            conversation_id=conv_id,
            role="user",
            content="Yo tener veinte años",
            input_source="keyboard",
        ).id
        harness.correction_storage.save_feedback(corrected, [_correction()])
        return corrected, clean

    def _tool_result(self, harness, path: str, payload: dict) -> str:
        response = harness.client.post(f"/api/learning/{path}", json=payload)
        assert response.status_code == 200
        return response.json()["result"]

    def test_grammar_returns_the_same_result_either_way(self, make_harness) -> None:
        harness = make_harness(mode="strict")
        conv_id = harness.create_conversation()
        corrected, clean = self._seed_corrected_and_clean_messages(harness, conv_id)

        with_feedback = self._tool_result(
            harness, "grammar", {"message_id": corrected, "content": "Yo tener veinte años"}
        )
        without_feedback = self._tool_result(
            harness, "grammar", {"message_id": clean, "content": "Yo tener veinte años"}
        )

        assert with_feedback == without_feedback

    def test_the_grammar_result_is_not_prefilled_by_the_correction(self, make_harness) -> None:
        harness = make_harness(mode="strict")
        conv_id = harness.create_conversation()
        corrected, _ = self._seed_corrected_and_clean_messages(harness, conv_id)

        result = self._tool_result(
            harness, "grammar", {"message_id": corrected, "content": "Yo tener veinte años"}
        )

        assert result == "".join(["Buenos", " días"])

    def test_translate_returns_the_same_result_either_way(self, make_harness) -> None:
        harness = make_harness(mode="strict")
        conv_id = harness.create_conversation()
        corrected, clean = self._seed_corrected_and_clean_messages(harness, conv_id)

        payload = {"content": "Yo tener veinte años", "native_language": "English"}
        with_feedback = self._tool_result(
            harness, "translate", {**payload, "message_id": corrected}
        )
        without_feedback = self._tool_result(harness, "translate", {**payload, "message_id": clean})

        assert with_feedback == without_feedback

    def test_phrasing_returns_the_same_result_either_way(self, make_harness) -> None:
        harness = make_harness(mode="strict")
        conv_id = harness.create_conversation()
        corrected, clean = self._seed_corrected_and_clean_messages(harness, conv_id)

        payload = {"content": "Yo tener veinte años", "target_language": "Spanish"}
        with_feedback = self._tool_result(harness, "phrasing", {**payload, "message_id": corrected})
        without_feedback = self._tool_result(harness, "phrasing", {**payload, "message_id": clean})

        assert with_feedback == without_feedback

    def test_the_correction_row_survives_a_grammar_check(self, make_harness) -> None:
        harness = make_harness(mode="strict")
        conv_id = harness.create_conversation()
        corrected, _ = self._seed_corrected_and_clean_messages(harness, conv_id)

        self._tool_result(
            harness, "grammar", {"message_id": corrected, "content": "Yo tener veinte años"}
        )

        assert len(harness.correction_storage.list_feedback(conv_id)) == 1
