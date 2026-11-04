"""011 T066: SubjectCheck, one structured call judging Today's subject (research R14)."""

import logging

import pytest

from app.podcasts.services.subject_check import SubjectCheck, SubjectDeclined
from app.practice_languages import ConversationLanguages
from app.services.llm.base import LLMError
from tests.support.scripted_show_llm import ScriptedShowLLM

SPANISH = ConversationLanguages.of("es", "en")
SUITABLE = {"is_suitable": True, "decline_reason": ""}
DECLINED = {"is_suitable": False, "decline_reason": "It asks how to hurt someone."}


def test_it_makes_one_structured_call_with_the_suitability_rule():
    llm = ScriptedShowLLM(SUITABLE)

    SubjectCheck(llm).check("why we yawn", SPANISH)

    assert len(llm.calls) == 1
    assert "why we yawn" in llm.last_prompt
    assert "hateful, sexual or dangerous" in llm.last_prompt
    assert set(llm.schemas[0]["required"]) == {"is_suitable", "decline_reason"}


def test_a_suitable_subject_passes():
    SubjectCheck(ScriptedShowLLM(SUITABLE)).check("why we yawn", SPANISH)


def test_an_unsuitable_subject_is_declined_with_its_reason_logged_not_raised(caplog):
    with caplog.at_level(logging.INFO), pytest.raises(SubjectDeclined) as raised:
        SubjectCheck(ScriptedShowLLM(DECLINED)).check("something awful", SPANISH)

    assert "hurt" not in str(raised.value)
    assert "It asks how to hurt someone." in caplog.text


def test_a_provider_failure_is_raised_unchanged():
    llm = ScriptedShowLLM(SUITABLE)
    llm.error = LLMError("down", "Ollama isn't running.")

    with pytest.raises(LLMError) as raised:
        SubjectCheck(llm).check("why we yawn", SPANISH)
    assert raised.value is llm.error
