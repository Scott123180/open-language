"""EpisodeEndings: how the turn code reports a finished episode, knowing nothing of memory.

`EpisodeTurns` depends on this one-method interface; the composition root wires it to the
memory keeper (010 research R6, DIP).
"""

from abc import ABC, abstractmethod


class EpisodeEndings(ABC):
    @abstractmethod
    def episode_finished(self, conversation_id: int) -> None:
        """The episode's sign-off line has been stored."""


class NoEpisodeEndings(EpisodeEndings):
    """Nobody listens: for tests and wiring where nothing follows an episode's end."""

    def episode_finished(self, conversation_id: int) -> None:
        return None
