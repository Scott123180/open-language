"""What to tell the learner when a language has fewer than two voices (spec edge case).

With one installed voice both hosts share it and every line is labelled with its speaker; with
none, the episode runs as text. Neither case ever borrows another language's voice (FR-031).
"""

from app.podcasts.services.episodes import LoadedEpisode
from app.practice_languages import language_name

SETUP_COMMAND = "./run.sh --setup"


def shared_voice_notice(language: str) -> str:
    name = language_name(language)
    return (
        f"Only one {name} voice is installed, so both hosts will share it. Every line shows "
        f"who is speaking. Run {SETUP_COMMAND} to add another {name} voice."
    )


def no_voice_message(language: str) -> str:
    name = language_name(language)
    return (
        f"No {name} voice is installed, so the hosts can't be read aloud. "
        f"Run {SETUP_COMMAND} to download one. You can still follow every episode in text."
    )


def catalogue_notices(language: str, installed_count: int) -> dict[str, str | None]:
    return {
        "shared_voice_notice": shared_voice_notice(language) if installed_count == 1 else None,
        "unavailable_message": no_voice_message(language) if installed_count == 0 else None,
    }


def episode_voice_notice(episode: LoadedEpisode) -> str | None:
    """The shared-voice notice for an episode whose two hosts speak with one voice."""
    voices = {host.voice_key for host in episode.hosts}
    if len(episode.hosts) < 2 or len(voices) > 1:
        return None
    return shared_voice_notice(episode.record.target_language)
