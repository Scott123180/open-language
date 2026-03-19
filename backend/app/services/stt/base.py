from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


class STTError(Exception):
    pass


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    detected_language: str | None


class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path, language_hint: str | None = None) -> TranscriptionResult:
        """Transcribe a 16kHz mono WAV file. Raises STTError on failure."""
        ...
