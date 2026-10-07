"""Applying a valid pack: derive, fetch voices, then write both data files all or nothing (R9).

Voices download first: they live outside the repository, are verified and idempotent, so a later
failure leaves only harmless downloads. The two data files are staged beside their targets and
swapped in with `os.replace`; if the second swap fails, the first target is restored.
"""

import difflib
import os
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from language_kit.checking import is_installed
from language_kit.composition import Kit
from language_kit.errors import KitExternalError
from language_kit.language_files import LanguageData
from language_kit.pack_check import PackCheck
from language_kit.render import derive, render
from language_kit.voices import VoiceCandidate, VoiceDownload

STAGED_SUFFIX = ".tmp"


@dataclass(frozen=True, slots=True)
class FileChange:
    path: Path
    text: str
    added: int
    removed: int


@dataclass(frozen=True, slots=True)
class ApplyPlan:
    language: LanguageData
    changes: tuple[FileChange, ...]
    voices: tuple[VoiceCandidate, ...]
    """Voices to ensure: the ones the pack adds and the ones missing from the voice directory."""

    @property
    def is_empty(self) -> bool:
        return not self.changes and not self.voices


def plan_apply(kit: Kit, check: PackCheck) -> ApplyPlan:
    merged = check.pack.merged_onto(check.existing)
    language = derive(merged, check.others, kit.voice_catalogue)
    files = render(language, kit.requirements)
    targets = (
        (kit.workspace.runtime_dir / f"{language.code}.toml", files.runtime),
        (kit.workspace.evaluation_dir / f"{language.code}.toml", files.evaluation),
    )
    changes = tuple(
        change for path, text in targets if text is not None if (change := _change(path, text))
    )
    return ApplyPlan(language, changes, _voices_to_ensure(kit, language, check.added_voices()))


def ensure_voices(kit: Kit, voices: Iterable[VoiceCandidate]) -> list[VoiceDownload]:
    voices = list(voices)
    if voices and kit.downloader is None:
        raise KitExternalError("voices are needed but no voice downloader is configured")
    return [kit.downloader.ensure(voice) for voice in voices] if kit.downloader else []


def write_atomically(changes: Iterable[FileChange]) -> None:
    staged = [(change.path, _stage(change)) for change in changes]
    backups = {path: path.read_bytes() if path.exists() else None for path, _ in staged}
    replaced: list[Path] = []
    try:
        for path, temporary in staged:
            os.replace(temporary, path)
            replaced.append(path)
    except OSError as error:
        _restore(replaced, backups)
        for _, temporary in staged:
            temporary.unlink(missing_ok=True)
        raise KitExternalError(
            f"writing the data files failed ({error}); they are unchanged"
        ) from error


def _change(path: Path, text: str) -> FileChange | None:
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    if current == text:
        return None
    diff = list(difflib.unified_diff(current.splitlines(), text.splitlines(), lineterm="", n=0))
    added = sum(line.startswith("+") and not line.startswith("+++") for line in diff)
    removed = sum(line.startswith("-") and not line.startswith("---") for line in diff)
    return FileChange(path, text, added, removed)


def _voices_to_ensure(
    kit: Kit, language: LanguageData, added: list[str]
) -> tuple[VoiceCandidate, ...]:
    voices = language.get("voices") or []
    keys = [str(voice.get("key")) for voice in voices if isinstance(voice, dict)]
    needed = [key for key in keys if key in added or not is_installed(key, kit.workspace.voice_dir)]
    if needed and kit.voice_catalogue is None:
        raise KitExternalError(
            f"voices {', '.join(needed)} are needed but the voice catalogue is unavailable"
        )
    return tuple(_catalogue_voice(kit, key) for key in needed)


def _catalogue_voice(kit: Kit, key: str) -> VoiceCandidate:
    voice = kit.voice_catalogue.voice(key) if kit.voice_catalogue else None
    if voice is None:
        raise KitExternalError(f"voice {key} is not in the voice catalogue")
    return voice


def _stage(change: FileChange) -> Path:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=change.path.parent, suffix=STAGED_SUFFIX, delete=False
    ) as staged:
        staged.write(change.text)
    return Path(staged.name)


def _restore(replaced: list[Path], backups: dict[Path, bytes | None]) -> None:
    for path in replaced:
        backup = backups[path]
        if backup is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(backup)
