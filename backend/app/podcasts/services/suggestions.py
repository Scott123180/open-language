"""Reply suggestions at the learner's turn: the roleplay suggestion prompt over the episode.

The prompt builder and level renderer are the roleplay's own, unchanged. Only the transcript
differs: each line is labelled with its host's name or the learner's label (contracts §8).
"""

import re

from app.conversation_levels import ConversationLevel, with_learner_text_rules
from app.podcasts.services.episodes import LoadedEpisode
from app.prompts.templates import build_suggestion_prompt

_LIST_MARKER = re.compile(r"^[\d\.\-\s]+")


def suggestion_prompt(episode: LoadedEpisode, count: int, level: ConversationLevel) -> str:
    prompt = build_suggestion_prompt(_transcript(episode), episode.languages.target_name, count)
    return with_learner_text_rules(prompt, level)


def parse_suggestions(text: str, count: int) -> list[str]:
    """Numbered or bulleted lines, markers stripped; the whole text if there are none."""
    lines = (line.strip() for line in text.strip().split("\n"))
    listed = [line for line in lines if line[:1].isdigit() or line.startswith("-")]
    stripped = (_LIST_MARKER.sub("", line).strip() for line in listed)
    suggestions = [suggestion for suggestion in stripped if suggestion]
    return (suggestions or [text.strip()])[:count]


def _transcript(episode: LoadedEpisode) -> str:
    return "\n".join(f"{_speaker(episode, line)}: {line.content}" for line in episode.lines)


def _speaker(episode: LoadedEpisode, line) -> str:
    if line.host is None:
        return episode.learner_label
    return episode.host_by_id(line.host.host_id).name
