from abc import ABC, abstractmethod
from pathlib import Path


class TTSError(Exception):
    pass


class VoiceUnavailable(TTSError):  # noqa: N818 — the name is fixed by contracts/api.md §9
    """The voice for a text's language is not installed. Nothing was spoken instead."""

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: Path) -> None:
        """Synthesize text to WAV at output_path. Raises TTSError on failure."""
        ...

    @property
    @abstractmethod
    def voice_name(self) -> str:
        """The voice model in use."""
        ...


class VoiceInstallation(ABC):
    @abstractmethod
    def is_installed(self, voice_key: str) -> bool:
        """Whether the voice's files are present, so it can speak without a network."""
        ...


class MessageVoiceLookup(ABC):
    """The voice one message must be spoken in, when it is not its conversation's voice.

    Declared by its consumer, the audio router, so that router never learns who speaks a
    message (ISP, DIP). A podcast host's line answers with the host's voice.
    """

    DEFAULT_UNAVAILABLE_MESSAGE = (
        "The voice for this line isn't installed, so it can't be read aloud. "
        "Run ./run.sh --setup to download it. You can keep going in text."
    )

    @abstractmethod
    def voice_for_message(self, message_id: int) -> str | None:
        """The message's own voice key, or None to use its conversation's voice."""

    def unavailable_message(self, message_id: int) -> str:
        """What to tell the learner when the message's own voice is not installed."""
        return self.DEFAULT_UNAVAILABLE_MESSAGE
