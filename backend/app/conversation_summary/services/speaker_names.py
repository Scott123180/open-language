"""SpeakerNames: who said each line, as the summary should name them (FR-037).

Declared by its consumer, the summariser. The podcast module supplies the names of an episode's
speakers; everything else is a roleplay, summarised as "Learner" and "Partner".
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping


class SpeakerNames(ABC):
    @abstractmethod
    def names_for(self, conversation_id: int) -> Mapping[int, str] | None:
        """A label per message id, or None when the conversation has no named speakers."""
