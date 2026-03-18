# Service Interface Contracts: Speak — Role-Play Conversation Chat

**Branch**: `001-speak-roleplay-chat` | **Date**: 2026-03-17

All services are declared as Python Abstract Base Classes before any concrete implementation is written (Constitution V: Extensibility). Factory functions return the configured concrete instance; callers depend only on the ABC.

---

## ScenarioProvider

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    description: str
    ai_context_prompt: str
    target_language_hint: str | None = None

class ScenarioProvider(ABC):
    @abstractmethod
    def get_random(self, exclude_id: str | None = None) -> Scenario:
        """Return a random scenario, never the one with exclude_id."""
        ...

    @abstractmethod
    def get_all(self) -> list[Scenario]:
        """Return all available scenarios."""
        ...
```

**Concrete implementation**: `StaticScenarioProvider` — loads from a hard-coded list.
**Future implementations**: `GenerativeScenarioProvider`, `RemoteScenarioProvider`.
**Contract test**: `get_random(exclude_id=X)` MUST never return the scenario with id `X` when more than one scenario exists.

---

## STTProvider

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    detected_language: str | None

class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path, language_hint: str | None = None) -> TranscriptionResult:
        """
        Transcribe audio file at audio_path.
        audio_path: path to a 16kHz mono WAV file.
        language_hint: BCP-47 code (e.g. 'es') to guide recognition; None = auto-detect.
        Returns TranscriptionResult; raises STTError on failure.
        """
        ...
```

**Concrete implementation**: `WhisperSTTProvider` — wraps `faster-whisper`.
**Preconditions**: Caller MUST convert audio to 16kHz mono WAV before calling `transcribe`.
**Exceptions**: `STTError` (custom) for transcription failures; `ValueError` if file does not exist.
**Threading**: Implementations MUST be safe to call from a `ThreadPoolExecutor` thread.

---

## LLMProvider

```python
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass

@dataclass(frozen=True)
class ChatMessage:
    role: str   # "system" | "user" | "assistant"
    content: str

class LLMProvider(ABC):
    @abstractmethod
    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        """
        Send a message list and yield response tokens one at a time.
        The last message in `messages` MUST be role="user".
        Yields: individual string tokens as they arrive.
        Raises: LLMError on model failure.
        """
        ...

    @abstractmethod
    def chat(self, messages: list[ChatMessage]) -> str:
        """
        Blocking (non-streaming) variant. Returns the full response string.
        Used for learning tools (grammar, translate, phrasing) where streaming adds no UX value.
        """
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model identifier in use (e.g. 'llama3.1')."""
        ...
```

**Concrete implementation**: `OllamaLLMProvider` — wraps `ollama.chat()`.
**Contract tests**:
- `chat_stream` MUST yield at least one token for any non-empty message list.
- `chat` result MUST equal the concatenation of all tokens from `chat_stream` for the same input.
- `model_name` MUST match the model used in actual API calls.

---

## TTSProvider

```python
from abc import ABC, abstractmethod
from pathlib import Path

class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: Path) -> None:
        """
        Synthesize text to speech and write WAV audio to output_path.
        output_path: caller-supplied destination (parent directory must exist).
        Raises: TTSError on synthesis failure.
        """
        ...

    @property
    @abstractmethod
    def voice_name(self) -> str:
        """The voice/model in use (e.g. 'es_ES-mls-medium')."""
        ...
```

**Concrete implementation**: `PiperTTSProvider` — uses `piper.voice.PiperVoice` (subprocess fallback).
**Threading**: Implementations MUST be safe to call from a `ThreadPoolExecutor` thread.
**Contract tests**:
- After `synthesize`, `output_path` MUST exist and be a valid WAV file (non-zero size).
- `voice_name` MUST match the voice used for synthesis.

---

## StorageProvider

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

# --- DTOs (data shapes crossing the storage boundary) ---

@dataclass
class ConversationRecord:
    id: int
    scenario_id: str
    scenario_title: str
    target_language: str
    native_language: str
    status: str          # "active" | "completed"
    started_at: datetime
    ended_at: datetime | None
    llm_model: str

@dataclass
class MessageRecord:
    id: int
    conversation_id: int
    role: str            # "user" | "assistant"
    content: str
    input_source: str | None
    created_at: datetime
    tts_audio_path: str | None

@dataclass
class LearningToolResultRecord:
    id: int
    message_id: int
    tool_type: str
    input_selection: str | None
    result: str
    created_at: datetime

@dataclass
class VocabularyItemRecord:
    id: int
    word: str
    translation: str
    target_language: str
    native_language: str
    source_conversation_id: int | None
    saved_at: datetime

@dataclass
class AppSettingsRecord:
    llm_model: str
    target_language: str
    native_language: str
    tts_voice: str
    suggestion_count: int

class StorageProvider(ABC):
    # --- Conversations ---
    @abstractmethod
    def create_conversation(self, scenario_id: str, scenario_title: str,
                            target_language: str, native_language: str,
                            llm_model: str) -> ConversationRecord: ...

    @abstractmethod
    def complete_conversation(self, conversation_id: int) -> ConversationRecord: ...

    @abstractmethod
    def get_conversation(self, conversation_id: int) -> ConversationRecord: ...

    @abstractmethod
    def list_conversations(self) -> list[ConversationRecord]: ...

    # --- Messages ---
    @abstractmethod
    def save_message(self, conversation_id: int, role: str, content: str,
                     input_source: str | None = None,
                     tts_audio_path: str | None = None) -> MessageRecord: ...

    @abstractmethod
    def get_messages(self, conversation_id: int) -> list[MessageRecord]: ...

    @abstractmethod
    def set_tts_path(self, message_id: int, path: str) -> None: ...

    # --- Learning Tools ---
    @abstractmethod
    def get_or_create_learning_result(self, message_id: int, tool_type: str,
                                       input_selection: str | None,
                                       compute: callable) -> LearningToolResultRecord:
        """
        Return cached result if it exists; otherwise call compute() to generate and cache it.
        compute: zero-argument callable returning the result string.
        """
        ...

    # --- Vocabulary ---
    @abstractmethod
    def save_vocabulary_item(self, word: str, translation: str,
                              target_language: str, native_language: str,
                              source_conversation_id: int | None) -> VocabularyItemRecord: ...

    @abstractmethod
    def list_vocabulary(self) -> list[VocabularyItemRecord]: ...

    # --- Settings ---
    @abstractmethod
    def get_settings(self) -> AppSettingsRecord: ...

    @abstractmethod
    def update_settings(self, **kwargs) -> AppSettingsRecord: ...
```

**Concrete implementation**: `SQLiteStorageProvider` — SQLAlchemy ORM, synchronous, WAL mode.
**Contract tests**: Each method MUST be tested against the concrete implementation with a temporary in-memory or file-based SQLite database.

---

## Factory Functions

```python
# backend/app/services/factory.py

def make_scenario_provider(settings: AppSettingsRecord) -> ScenarioProvider:
    return StaticScenarioProvider()

def make_stt_provider(settings: AppSettingsRecord) -> STTProvider:
    return WhisperSTTProvider(model_size="base", device="auto")

def make_llm_provider(settings: AppSettingsRecord) -> LLMProvider:
    return OllamaLLMProvider(model=settings.llm_model)

def make_tts_provider(settings: AppSettingsRecord) -> TTSProvider:
    return PiperTTSProvider(voice_name=settings.tts_voice)

def make_storage_provider() -> StorageProvider:
    return SQLiteStorageProvider(db_path=resolve_db_path())
```

Factories are called once at app startup; instances are injected into FastAPI routers via FastAPI dependency injection (`Depends`).
