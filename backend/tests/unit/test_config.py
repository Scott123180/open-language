"""Unit tests for the 004 additions to app.config.Settings."""

from pathlib import Path

import pytest

from app.config import Settings

_APP_HOME = Path.home() / ".open-language"


@pytest.fixture()
def settings(monkeypatch) -> Settings:
    for name in (
        "OPEN_LANGUAGE_CLAUDE_EXECUTABLE",
        "OPEN_LANGUAGE_CLAUDE_WORKDIR",
        "OPEN_LANGUAGE_CLAUDE_LOG_DIR",
        "OPEN_LANGUAGE_CLAUDE_REQUEST_TIMEOUT_SECONDS",
        "OPEN_LANGUAGE_SESSION_MAX_LIVE",
        "OPEN_LANGUAGE_SESSION_IDLE_TTL_MINUTES",
    ):
        monkeypatch.delenv(name, raising=False)
    return Settings(_env_file=None)


def test_claude_executable_defaults_to_claude_on_path(settings):
    assert settings.claude_executable == "claude"


def test_claude_workdir_defaults_to_an_app_owned_directory(settings):
    assert settings.claude_workdir == _APP_HOME / "claude-workdir"


def test_claude_log_dir_defaults_to_a_sibling_of_the_workdir(settings):
    assert settings.claude_log_dir == _APP_HOME / "claude-logs"
    assert settings.claude_log_dir != settings.claude_workdir


def test_claude_request_timeout_defaults_to_two_minutes(settings):
    assert settings.claude_request_timeout_seconds == 120.0


def test_session_max_live_defaults_to_three(settings):
    assert settings.session_max_live == 3


def test_session_idle_ttl_defaults_to_thirty_minutes(settings):
    assert settings.session_idle_ttl_minutes == 30


def test_claude_executable_is_overridable_from_the_environment(monkeypatch):
    monkeypatch.setenv("OPEN_LANGUAGE_CLAUDE_EXECUTABLE", "/nonexistent")

    assert Settings(_env_file=None).claude_executable == "/nonexistent"


def test_claude_directories_expand_the_home_shortcut(monkeypatch):
    monkeypatch.setenv("OPEN_LANGUAGE_CLAUDE_WORKDIR", "~/cw")
    monkeypatch.setenv("OPEN_LANGUAGE_CLAUDE_LOG_DIR", "~/cl")

    configured = Settings(_env_file=None)

    assert configured.claude_workdir == Path.home() / "cw"
    assert configured.claude_log_dir == Path.home() / "cl"
