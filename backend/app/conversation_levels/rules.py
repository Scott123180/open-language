"""Turning a level into instruction text appended to an existing prompt (005 research R3–R6).

All three public functions are pure. At a level without limits (Natural) they return the prompt
unchanged, byte for byte, so FR-004 holds by construction. The blocks are short, numeric and
imperative, carry no example sentences in any language, and never mention the learner's native
language, so the prompt's own language rule stays the only statement about it (FR-015).
"""

from app.conversation_levels.catalog import LEVEL_CATALOG, ConversationLevel, SpeechLimits

_BLOCK_SEPARATOR = "\n\n"
_PARTNER_PRECEDENCE = "These rules about how you speak override anything above."
_LEARNER_PRECEDENCE = (
    "These rules limit the target-language words the learner will say or read, "
    "and override anything above."
)
_PARTNER_BEHAVIOUR = (
    "- These are limits, not targets: you may always speak more simply, never more complexly.",
    "- You may use a few words above this level only when they are essential to the scenario's "
    "topic, or when the learner has just used them.",
    "- If the learner writes above this level, still answer what the learner said, "
    "but keep your own reply within these rules.",
    "- If the learner asks you to speak more simply or says they do not understand, "
    "make that reply even simpler.",
)
_LEARNER_SCOPE = "- Explanations in any other language are not limited by these rules."


def with_partner_speech_rules(prompt: str, level: ConversationLevel) -> str:
    """Append the rules for how the conversation partner speaks at `level`."""
    limits = LEVEL_CATALOG[level].limits
    if limits is None:
        return prompt
    return prompt + _BLOCK_SEPARATOR + _partner_speech_block(limits)


def with_sentence_rules(prompt: str, level: ConversationLevel) -> str:
    """Append the partner's rules for each sentence at `level`, with no cap on how many.

    For a speaker whose line length is set elsewhere, such as a podcast host (011 research R2).
    """
    limits = LEVEL_CATALOG[level].limits
    if limits is None:
        return prompt
    return prompt + _BLOCK_SEPARATOR + _sentence_block(limits)


def with_learner_text_rules(prompt: str, level: ConversationLevel) -> str:
    """Append the rules for target-language text the learner will say or read at `level`."""
    limits = LEVEL_CATALOG[level].limits
    if limits is None:
        return prompt
    return prompt + _BLOCK_SEPARATOR + _learner_text_block(limits)


def _partner_speech_block(limits: SpeechLimits) -> str:
    cap_line = f"- Say at most {limits.max_sentences_per_reply} sentences per reply."
    return "\n".join((_PARTNER_PRECEDENCE, cap_line, *_sentence_lines(limits)))


def _sentence_block(limits: SpeechLimits) -> str:
    return "\n".join((_PARTNER_PRECEDENCE, *_sentence_lines(limits)))


def _sentence_lines(limits: SpeechLimits) -> tuple[str, ...]:
    return (
        *_shared_lines(limits),
        f"- Questions to the learner: {limits.questions}.",
        *_PARTNER_BEHAVIOUR,
    )


def _learner_text_block(limits: SpeechLimits) -> str:
    lines = (_LEARNER_PRECEDENCE, *_shared_lines(limits), _LEARNER_SCOPE)
    return "\n".join(lines)


def _shared_lines(limits: SpeechLimits) -> tuple[str, ...]:
    return (
        f"- Use at most {limits.max_words_per_sentence} words per sentence, "
        f"{limits.sentence_joining}.",
        f"- Tenses: {limits.tenses}.",
        f"- Vocabulary: only the {limits.vocabulary_rank} most common words of the language.",
        f"- Idioms and slang: {limits.idioms}.",
    )
