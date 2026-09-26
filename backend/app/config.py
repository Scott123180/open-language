from functools import lru_cache
from pathlib import Path
from typing import Literal

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
    low_confidence_threshold: float = 0.55
    correction_timeout_seconds: float = 8.0
    claude_executable: str = "claude"
    claude_workdir: Path = Path.home() / ".open-language" / "claude-workdir"
    claude_log_dir: Path = Path.home() / ".open-language" / "claude-logs"
    claude_request_timeout_seconds: float = 120.0
    session_max_live: int = 3
    session_idle_ttl_minutes: int = 30
    host: str = "127.0.0.1"
    port: int = 8000
    # Development leaves the frontend to Vite; only production serves the built copy.
    mode: Literal["development", "production"] = "development"

    model_config = {
        "env_prefix": "OPEN_LANGUAGE_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    @field_validator("db_path", "voice_dir", "claude_workdir", "claude_log_dir", mode="after")
    @classmethod
    def expand_user(cls, v: Path) -> Path:
        return v.expanduser()

    @property
    def is_production(self) -> bool:
        return self.mode == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
