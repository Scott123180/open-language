"""T077: the summary prompt holds only the labelled transcript and its rules (FR-036–FR-039)."""

import re

from app.conversation_levels import ConversationLevel, with_learner_text_rules
from app.conversation_summary.prompts import (
    SIMPLE_SENTENCES_RULE,
    build_summary_prompt,
    conversation_language_rules,
)
from app.practice_languages import ConversationLanguages

GERMAN = ConversationLanguages.of("de", "en")
TRANSCRIPT = "Lena: Die Markthalle ist toll.\nJonas: Zu teuer!"


def _prompt(level=ConversationLevel.NATURAL, has_names=True, previous=()):
    return build_summary_prompt(TRANSCRIPT, GERMAN, level, has_names, previous)


def test_the_prompt_holds_the_labelled_transcript():
    assert TRANSCRIPT in _prompt()


def test_the_rules_keep_to_what_was_said_and_to_five_points():
    prompt = _prompt()

    assert "Use only what was said" in prompt
    assert "at most 5 points" in prompt
    assert "where the conversation stands now" in prompt


def test_the_hosts_are_named_behind_their_points_when_names_are_given():
    assert "name the speaker" in _prompt(has_names=True)
    assert "name the speaker" not in _prompt(has_names=False)


def test_languages_are_named_never_given_as_codes():
    prompt = _prompt()

    assert "German" in prompt and "English" in prompt
    assert not re.search(r"\b(de|en)\b", prompt)


def test_the_conversation_language_follows_the_level_and_stays_simple_at_natural():
    natural = conversation_language_rules(GERMAN, ConversationLevel.NATURAL)
    beginner = conversation_language_rules(GERMAN, ConversationLevel.BEGINNER)

    assert SIMPLE_SENTENCES_RULE in natural and SIMPLE_SENTENCES_RULE in beginner
    assert beginner == with_learner_text_rules(natural, ConversationLevel.BEGINNER)
    assert beginner in _prompt(level=ConversationLevel.BEGINNER)


def test_a_fold_carries_the_earlier_points():
    assert "They talked about markets." in _prompt(previous=("They talked about markets.",))
