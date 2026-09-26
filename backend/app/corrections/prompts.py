"""Prompts owned by the corrections module.

The evaluation prompt carries FR-007's negative instructions: the guards that
decide what is *not* worth correcting are a judgement call, and a prompt is the
right place for a judgement call. Only the word-count guard lives in code.
"""

from app.corrections.config import MAX_CORRECTIONS_PER_MESSAGE

# The verdict field is not decoration: asking the model to commit to "correct"
# before it may list anything halves its false-positive rate on clean sentences.
CORRECTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["correct", "has_mistakes"]},
        "corrections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["conjugation", "agreement", "word_choice", "word_order"],
                    },
                    "error_fragment": {"type": "string"},
                    "corrected_text": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["category", "error_fragment", "corrected_text", "explanation"],
            },
        },
    },
    "required": ["verdict", "corrections"],
}


def build_evaluation_prompt(
    learner_text: str,
    target_language: str,
    native_language: str,
    preceding_character_line: str | None,
) -> str:
    context = (
        f'Context — what the character just said: """{preceding_character_line}"""\n\n'
        if preceding_character_line
        else ""
    )
    return (
        f"You are a strict {target_language} examiner reviewing one sentence written by a "
        f"native {native_language} speaker learning {target_language}.\n\n"
        f"Answer in two steps.\n"
        f'Step 1 — set "verdict": is this sentence correct {target_language} as written? '
        f"Most sentences you see are already correct. Reporting nothing is the normal, expected "
        f'answer. Answer "correct" unless you are certain a native speaker would call it wrong.\n'
        f'Step 2 — only if the verdict is "has_mistakes", list the mistakes. When the verdict is '
        f'"correct", "corrections" MUST be an empty list.\n\n'
        f"Only these count as mistakes: verb conjugation, agreement of gender and number, "
        f"word choice where the wrong word changes the meaning, and word order that breaks "
        f"the sentence.\n\n"
        f"Never report any of the following:\n"
        f"- a missing or wrong diacritic or accent mark\n"
        f"- a word or construction that is valid in some region where {target_language} is spoken\n"
        f"- phrasing that is understandable and correct but merely unidiomatic\n"
        f"- a stylistic preference, or another tense that would also be correct\n"
        f"- capitalisation, spacing, or punctuation\n"
        f"- praise, encouragement, or any comment on what the learner got right\n\n"
        f"Never invent a mistake to seem helpful: a false correction actively harms the learner.\n\n"
        f"Report at most {MAX_CORRECTIONS_PER_MESSAGE} corrections, most damaging to "
        f"comprehension first.\n\n"
        f"For each correction: error_fragment is the learner's own wrong words, copied exactly "
        f"from the sentence; corrected_text is the learner's whole sentence rewritten correctly "
        f"in {target_language}; explanation says what was wrong, in one or two sentences, "
        f"written in {native_language}.\n\n"
        f"{context}"
        f'Learner sentence: """{learner_text}"""\n\n'
        f"Respond with JSON and nothing else."
    )


def build_recast_instruction(corrected_text: str, target_language: str) -> str:
    """The Gentle-mode suffix: restate the corrected form inside the reply (FR-012)."""
    return (
        f"\n\nThe learner's last message contained a mistake. Reply in character as usual, "
        f'but work the corrected form naturally into your own words: "{corrected_text}". '
        f"Do not point out the mistake, do not explain it, and do not ask the learner to "
        f"repeat anything — simply say it correctly yourself as part of what you were "
        f"going to say. Every word of your reply stays in {target_language}."
    )


def build_repeat_request(target_language: str) -> str:
    """The FR-027 ask-to-repeat text, in the learner's own language."""
    return (
        "I didn't quite catch that — could you say it again? "
        f"Try to speak clearly in {target_language}."
    )
