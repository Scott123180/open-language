"""T006: the turn mechanics moved out of the chat router keep their shape (research R11).

The behavioural net for the move is the existing chat and corrections suites, which pass
unmodified. These tests pin only the package's import surface.
"""

import app.conversation_turns as conversation_turns
from app.conversation_turns import LearnerMessageRequest, sse

PUBLIC_NAMES = {
    "sse",
    "EngineTurn",
    "SavedReply",
    "relay_engine_reply",
    "start_warming",
    "LearnerMessageRequest",
    "save_learner_message",
    "Corrections",
    "plan_learner_turn",
    "schedule_speech",
}


def test_the_package_exports_exactly_its_public_interface():
    assert set(conversation_turns.__all__) == PUBLIC_NAMES


def test_sse_frames_a_payload_as_one_data_event():
    assert sse({"a": 1}) == 'data: {"a": 1}\n\n'


def test_a_typed_message_carries_no_spoken_confidence():
    request = LearnerMessageRequest(
        content="x", input_source="keyboard", transcription_confidence=0.2
    )

    assert request.spoken_confidence is None


def test_a_spoken_message_carries_its_confidence():
    request = LearnerMessageRequest(content="x", input_source="voice", transcription_confidence=0.2)

    assert request.spoken_confidence == 0.2


def test_the_chat_router_keeps_its_request_name():
    from app.routers.chat import ChatMessageRequest

    assert ChatMessageRequest is LearnerMessageRequest
