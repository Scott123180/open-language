"""Checking a language's data against the registry, shared by check, validate and backfill."""

from collections.abc import Iterable
from pathlib import Path

from language_kit.context import RuleContext
from language_kit.findings import Finding
from language_kit.language_files import LanguageData, catalogued_codes, read_language
from language_kit.registry import Requirement
from language_kit.workspace import Workspace

VOICE_FILE_SUFFIXES = (".onnx", ".onnx.json")


def checked(requirements: Iterable[Requirement]) -> tuple[Requirement, ...]:
    """The requirements `check` runs: every one that is not onboarding-only."""
    return tuple(item for item in requirements if not item.onboarding_only)


def failing_items(
    language: LanguageData,
    others: tuple[LanguageData, ...],
    context: RuleContext,
    requirements: Iterable[Requirement],
) -> dict[str, list[Finding]]:
    """The findings of every requirement that has any, keyed by requirement path, in order."""
    focused = context.for_language(language, others)
    results = {item.path: item.findings(focused) for item in requirements}
    return {path: findings for path, findings in results.items() if findings}


def catalogued_languages(workspace: Workspace) -> dict[str, LanguageData]:
    """Every catalogued language's data, in display order."""
    return {code: read_language(code, workspace) for code in catalogued_codes(workspace)}


def others_than(code: str, languages: dict[str, LanguageData]) -> tuple[LanguageData, ...]:
    return tuple(language for other, language in languages.items() if other != code)


def installed_voices(language: LanguageData, voice_dir: Path) -> tuple[int, int]:
    """How many of the language's voices have both files in the voice directory, of how many."""
    keys = [voice.get("key") for voice in language.get("voices") or [] if isinstance(voice, dict)]
    installed = [key for key in keys if isinstance(key, str) and is_installed(key, voice_dir)]
    return len(installed), len(keys)


def is_installed(key: str, voice_dir: Path) -> bool:
    return all((voice_dir / f"{key}{suffix}").is_file() for suffix in VOICE_FILE_SUFFIXES)
