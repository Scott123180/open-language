from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_path: Path = Path.home() / ".open-language" / "app.db"
    tts_voice: str = "es_ES-davefx-medium"
    voice_dir: Path = Path.home() / ".local" / "share" / "piper-voices"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    whisper_model: str = "base"
    whisper_device: str = "auto"
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = {
        "env_prefix": "OPEN_LANGUAGE_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    @field_validator("db_path", "voice_dir", mode="after")
    @classmethod
    def expand_user(cls, v: Path) -> Path:
        return v.expanduser()


@lru_cache
def get_settings() -> Settings:
    return Settings()
