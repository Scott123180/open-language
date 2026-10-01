"""Reading a stored reply aloud in the background, into the shared speech cache."""

from pathlib import Path

from app.services.storage.base import StorageProvider
from app.services.tts.base import TTSProvider


def _tts_cache_dir() -> Path:
    return Path.home() / ".open-language" / "tts_cache"


def schedule_speech(loop, storage: StorageProvider, tts: TTSProvider, message_id: int, text: str):
    cache_dir = _tts_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    audio_path = cache_dir / f"{message_id}.wav"

    def _synthesize():
        tts.synthesize(text, audio_path)
        storage.set_tts_path(message_id, str(audio_path))

    loop.run_in_executor(None, _synthesize)
