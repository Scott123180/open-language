"""T006: LLMError carries a learner-facing message and a retry hint."""

from app.services.llm.base import LLMError


def test_default_user_message_is_the_existing_sentence():
    assert LLMError("x").user_message == "The AI is not responding. Please try again."
    assert LLMError.DEFAULT_USER_MESSAGE == "The AI is not responding. Please try again."


def test_custom_user_message_is_returned():
    assert LLMError("x", user_message="Custom").user_message == "Custom"


def test_str_keeps_the_technical_detail():
    assert "detail" in str(LLMError("detail"))


def test_can_retry_defaults_to_true():
    assert LLMError("x").can_retry is True


def test_can_retry_can_be_turned_off():
    assert LLMError("x", can_retry=False).can_retry is False
