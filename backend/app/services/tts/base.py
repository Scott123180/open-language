from abc import ABC, abstractmethod
from pathlib import Path


class TTSError(Exception):
    pass


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
