"""Where the kit works: the repository, its two data directories, the voices and the output."""

__all__ = ["EVALUATION_DIR", "RUNTIME_DIR", "KitUsageError", "Workspace"]

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from language_kit.errors import KitUsageError

RUNTIME_DIR = Path("backend/app/language_data/languages")
EVALUATION_DIR = Path("backend/tests/integration/practice_languages/evaluation")
ROOT_MARKER = Path("backend/pyproject.toml")
FEATURE_FILE = Path(".specify/feature.json")
LANGUAGES_FOLDER = "languages"
VOICE_DIR_VARIABLE = "OPEN_LANGUAGE_VOICE_DIR"
DEFAULT_VOICE_DIR = Path(".local/share/piper-voices")
CALLER_DIR_VARIABLE = "LANGUAGE_KIT_CWD"
"""Set by kit.sh: the directory it was run from, before it changes into backend/."""


@dataclass(frozen=True, slots=True)
class Workspace:
    root: Path
    voice_dir: Path
    out: Path | None = None
    caller_dir: Path | None = None

    @classmethod
    def discover(
        cls, start: Path, out: Path | None = None, environ: Mapping[str, str] = os.environ
    ) -> "Workspace":
        voice_dir = environ.get(VOICE_DIR_VARIABLE)
        voices = Path(voice_dir) if voice_dir else Path.home() / DEFAULT_VOICE_DIR
        caller = environ.get(CALLER_DIR_VARIABLE)
        root = _find_root(start.resolve())
        return cls(
            root=root, voice_dir=voices, out=out, caller_dir=Path(caller) if caller else None
        )

    @property
    def runtime_dir(self) -> Path:
        return self.root / RUNTIME_DIR

    @property
    def evaluation_dir(self) -> Path:
        return self.root / EVALUATION_DIR

    @property
    def output_root(self) -> Path:
        return self.out if self.out is not None else self._feature_directory() / LANGUAGES_FOLDER

    def language_dir(self, code: str) -> Path:
        return self.output_root / code

    def with_output(self, out: Path) -> "Workspace":
        return replace(self, out=out)

    def resolve(self, path: Path) -> Path:
        """A path given on the command line: from the caller's directory if it exists there, else the root."""
        if path.is_absolute():
            return path
        from_caller = (self.caller_dir or Path.cwd()) / path
        return from_caller if from_caller.exists() else self.root / path

    def relative(self, path: Path) -> str:
        """A path as shown in output and the run log: from the repository root when inside it."""
        return str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path)

    def _feature_directory(self) -> Path:
        feature_file = self.root / FEATURE_FILE
        if not feature_file.is_file():
            raise KitUsageError(f"{FEATURE_FILE} is missing: pass --out DIR for the kit's output")
        feature = json.loads(feature_file.read_text(encoding="utf-8"))
        return self.root / str(feature["feature_directory"])


def _find_root(start: Path) -> Path:
    for directory in (start, *start.parents):
        if (directory / ROOT_MARKER).is_file():
            return directory
    raise KitUsageError(f"no repository found above {start}: run the kit from the repository")
