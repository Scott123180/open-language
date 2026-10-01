"""The summary prompt and its JSON schema (research R13).

The prompt holds only the labelled transcript and the rules. Both languages come back in one
reply, so the two versions describe the same points by construction (FR-038, SC-013).
Languages are named ("German"), never given as codes.
"""

from app.conversation_levels import ConversationLevel, with_learner_text_rules
from app.practice_languages import ConversationLanguages

MAX_SUMMARY_POINTS = 5
SIMPLE_SENTENCES_RULE = "Use short, simple sentences, even when the conversation used long ones."

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "points": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_SUMMARY_POINTS,
            "items": {
                "type": "object",
                "properties": {
                    "conversation_language": {"type": "string"},
                    "english": {"type": "string"},
                },
                "required": ["conversation_language", "english"],
            },
        }
    },
    "required": ["points"],
}


def conversation_language_rules(languages: ConversationLanguages, level: ConversationLevel) -> str:
    """How the conversation-language version is written: simple always, and at the level (FR-039)."""
    target = languages.target_name
    rules = (
        f"For the {target} version of each point:\n"
        f"- {SIMPLE_SENTENCES_RULE}\n"
        f"- Write it entirely in {target}."
    )
    return with_learner_text_rules(rules, level)


def build_summary_prompt(
    transcript: str,
    languages: ConversationLanguages,
    level: ConversationLevel,
    has_names: bool,
    previous: tuple[str, ...] = (),
) -> str:
    sections = (
        _task(languages),
        _rules(languages, has_names),
        conversation_language_rules(languages, level),
        _previous(previous, languages),
        f"Transcript:\n{transcript}",
    )
    return "\n\n".join(section for section in sections if section)


def _task(languages: ConversationLanguages) -> str:
    return (
        f"Summarise the {languages.target_name} conversation below for a learner of "
        f"{languages.target_name} whose own language is {languages.native_name}."
    )


def _rules(languages: ConversationLanguages, has_names: bool) -> str:
    rules = [
        "Rules:",
        "- Use only what was said in the transcript. Never add anything that was not said.",
        f"- Give at most {MAX_SUMMARY_POINTS} points: fewer when little has been said.",
        "- Cover what has been discussed and the speakers' main points, and end with "
        "where the conversation stands now.",
        f"- Give every point in {languages.target_name} and in {languages.native_name}; "
        "both versions say the same thing.",
    ]
    if has_names:
        rules.append("- For each point, name the speaker who holds that view or told that story.")
    return "\n".join(rules)


def _previous(previous: tuple[str, ...], languages: ConversationLanguages) -> str:
    if not previous:
        return ""
    points = "\n".join(f"- {point}" for point in previous)
    return (
        f"Summary of the conversation before this part of the transcript, in "
        f"{languages.native_name} (fold it into your points):\n{points}"
    )
