"""011 T066a: SubjectSuggester, up to three new subjects for a show (FR-010a, research R20)."""

import json

import pytest

from app.podcasts.prompts import ShowBrief
from app.podcasts.services.subject_suggestions import SubjectRequest, SubjectSuggester
from app.practice_languages import ConversationLanguages
from app.services.llm.base import LLMError
from tests.support.scripted_show_llm import ScriptedShowLLM

SPANISH = ConversationLanguages.of("es", "en")
SHOW = ShowBrief("Big Little Questions", "Everyday curiosities.", "everyday curiosities", "guest")


def _request(**changes) -> SubjectRequest:
    values = {
        "show": SHOW,
        "languages": SPANISH,
        "interests": ("chess",),
        "covered": ("los bostezos",),
        "avoid": ("why bread goes stale",),
        **changes,
    }
    return SubjectRequest(**values)


def _suggest(subjects: list[str], request: SubjectRequest | None = None) -> tuple[str, ...]:
    return SubjectSuggester(ScriptedShowLLM({"subjects": subjects})).suggest(request or _request())


def test_one_structured_call_carries_the_show_interests_covered_and_avoided():
    llm = ScriptedShowLLM({"subjects": ["why cats purr"]})

    SubjectSuggester(llm).suggest(_request())

    prompt = llm.last_prompt
    assert len(llm.calls) == 1
    for expected in (
        "Big Little Questions",
        "Everyday curiosities.",
        "everyday curiosities",
        "chess",
        "los bostezos",
        "why bread goes stale",
        "in English",
        "hateful, sexual or dangerous",
    ):
        assert expected in prompt
    schema = llm.schemas[0]["properties"]["subjects"]
    assert (schema["minItems"], schema["maxItems"]) == (1, 3)


def test_subjects_are_trimmed_and_at_most_three():
    assert _suggest(["  why cats purr ", "why we hiccup", "why ice floats", "why sky is blue"]) == (
        "why cats purr",
        "why we hiccup",
        "why ice floats",
    )


def test_a_subject_over_120_characters_is_dropped():
    assert _suggest(["x" * 121, "why cats purr"]) == ("why cats purr",)


@pytest.mark.parametrize("repeat", ["Los Bostezos", "why bread goes stale", "Why cats purr"])
def test_a_covered_avoided_or_repeated_subject_is_dropped(repeat):
    assert _suggest(["why cats purr", repeat]) == ("why cats purr",)


def test_nothing_left_after_filtering_is_an_empty_answer():
    assert _suggest(["los bostezos"]) == ()


def test_a_provider_failure_is_raised_unchanged():
    llm = ScriptedShowLLM({"subjects": []})
    llm.error = LLMError("down", "Ollama isn't running.")

    with pytest.raises(LLMError) as raised:
        SubjectSuggester(llm).suggest(_request())
    assert raised.value is llm.error


def test_an_unreadable_reply_is_a_provider_error():
    llm = ScriptedShowLLM()
    llm.raw_reply = json.dumps({"nope": 1})

    with pytest.raises(LLMError):
        SubjectSuggester(llm).suggest(_request())
