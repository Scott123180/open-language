"""What other modules may ask about who speaks an episode's lines (contracts §12).

Both views are constructed only in `services/factory.py`, which wires them to the consumer
interfaces their callers declare.
"""

from collections.abc import Mapping

from app.podcasts.catalog import PODCAST_SCENARIO_ID
from app.podcasts.services.storage import HostRecord, PodcastStorage
from app.services.storage.base import StorageProvider
from app.services.tts.base import MessageVoiceLookup


def host_voice_unavailable_message(host_name: str) -> str:
    """The plain message for a host whose voice is not installed (FR-031, research R7)."""
    return (
        f"{host_name}'s voice isn't installed, so {host_name}'s lines can't be read aloud. "
        "Run ./run.sh --setup to download it. You can keep following in text."
    )


class _EpisodeHosts:
    """Finds the host behind a message, reading podcast rows only for an episode."""

    def __init__(self, podcasts: PodcastStorage, conversations: StorageProvider) -> None:
        self._podcasts = podcasts
        self._conversations = conversations

    def host_of(self, message_id: int) -> HostRecord | None:
        message = self._conversations.get_message(message_id)
        if message is None or not self.is_episode(message.conversation_id):
            return None
        lines = self._podcasts.get_lines(message.conversation_id)
        line = next((line for line in lines if line.message_id == message_id), None)
        if line is None or line.host is None:
            return None
        hosts = self._podcasts.get_hosts(message.conversation_id)
        return next(host for host in hosts if host.host_id == line.host.host_id)

    def is_episode(self, conversation_id: int) -> bool:
        conversation = self._conversations.get_conversation(conversation_id)
        return conversation is not None and conversation.scenario_id == PODCAST_SCENARIO_ID


class PodcastMessageVoices(MessageVoiceLookup):
    """A host line is spoken in its host's voice; every other message in its conversation's."""

    def __init__(self, podcasts: PodcastStorage, conversations: StorageProvider) -> None:
        self._hosts = _EpisodeHosts(podcasts, conversations)

    def voice_for_message(self, message_id: int) -> str | None:
        host = self._hosts.host_of(message_id)
        return host.voice_key if host is not None else None

    def unavailable_message(self, message_id: int) -> str:
        host = self._hosts.host_of(message_id)
        if host is None:
            return super().unavailable_message(message_id)
        return host_voice_unavailable_message(host.name)


class PodcastSpeakerNames:
    """Who said each line of an episode, for its summary (FR-037).

    Host lines are named by their host; learner lines by the name the hosts use, when there is
    one. A conversation that is not an episode has no names (None). The factory adapts this to
    the summary module's `SpeakerNames`; the two modules never import each other.
    """

    def __init__(self, podcasts: PodcastStorage, conversations: StorageProvider) -> None:
        self._podcasts = podcasts
        self._hosts = _EpisodeHosts(podcasts, conversations)

    def names_for(self, conversation_id: int) -> Mapping[int, str] | None:
        if not self._hosts.is_episode(conversation_id):
            return None
        episode = self._podcasts.get_episode(conversation_id)
        hosts = {host.host_id: host.name for host in self._podcasts.get_hosts(conversation_id)}
        return {
            line.message_id: hosts[line.host.host_id] if line.host else episode.learner_name
            for line in self._podcasts.get_lines(conversation_id)
            if line.host or episode.learner_name
        }
