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
