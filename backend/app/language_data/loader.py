"""Strict reading of the language data files: unknown, missing or mistyped keys are refused."""

import tomllib
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

from app.language_data.records import LanguageRecord, PodcastRecord, VoiceRecord

LANGUAGES_DIR = Path(__file__).resolve().parent / "languages"
LOCALE_SEPARATOR = "_"

_LANGUAGE_SCHEMA: Mapping[str, type] = {
    "code": str,
    "name": str,
    "order": int,
    "default_voice": str,
    "voices": list,
    "podcast": dict,
}
_VOICE_SCHEMA: Mapping[str, type] = {
    "key": str,
    "display_name": str,
    "gender": str,
    "locale": str,
    "quality": str,
    "speaking_rate": str,
}
_PODCAST_SCHEMA: Mapping[str, type] = {"host_names": dict, "guest_labels": list, "sample_line": str}


class LanguageDataError(ValueError):
    """A language data file is malformed or contradicts another; names the file and the key."""


def load_language_records(directory: Path = LANGUAGES_DIR) -> tuple[LanguageRecord, ...]:
    """Every language file, sorted by `order`. Strict: unknown/missing keys and wrong types raise."""
    records = tuple(_load_file(path) for path in sorted(directory.glob("*.toml")))
    _check_across_files(records)
    return tuple(sorted(records, key=lambda record: record.order))


def voice_keys(directory: Path = LANGUAGES_DIR) -> tuple[str, ...]:
    """Every voice key of every language, in language order (for run.sh)."""
    return tuple(
        voice.key for record in load_language_records(directory) for voice in record.voices
    )


def _load_file(path: Path) -> LanguageRecord:
    reader = _FileReader(path)
    record = reader.language(reader.document())
    reader.check_record(record)
    return record


class _FileReader:
    """Reads one file into a record; every error it raises names that file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def document(self) -> dict[str, Any]:
        try:
            return tomllib.loads(self._path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            raise self._error(f"is not valid TOML: {error}") from error

    def language(self, table: dict[str, Any]) -> LanguageRecord:
        self._check_table(table, _LANGUAGE_SCHEMA, "")
        voices = tuple(self._voice(voice, index) for index, voice in enumerate(table["voices"]))
        return LanguageRecord(
            code=table["code"],
            name=table["name"],
            order=table["order"],
            default_voice=table["default_voice"],
            voices=voices,
            podcast=self._podcast(table["podcast"]),
        )

    def check_record(self, record: LanguageRecord) -> None:
        if record.code != self._path.stem:
            raise self._error(f"key 'code' is {record.code!r} but must equal the file name")
        if record.default_voice not in {voice.key for voice in record.voices}:
            raise self._error(f"key 'default_voice' {record.default_voice!r} is not among voices")
        for voice in record.voices:
            if voice.locale.split(LOCALE_SEPARATOR)[0] != record.code:
                raise self._error(f"voice {voice.key!r}: key 'locale' must start with the code")

    def _voice(self, table: Any, index: int) -> VoiceRecord:
        where = f"voices[{index}]."
        if not isinstance(table, dict):
            raise self._error(f"key '{where[:-1]}' must be a table")
        self._check_table(table, _VOICE_SCHEMA, where)
        return VoiceRecord(**table)

    def _podcast(self, table: dict[str, Any]) -> PodcastRecord:
        self._check_table(table, _PODCAST_SCHEMA, "podcast.")
        host_names = {
            gender: self._strings(names, f"podcast.host_names.{gender}")
            for gender, names in table["host_names"].items()
        }
        return PodcastRecord(
            host_names=MappingProxyType(host_names),
            guest_labels=self._strings(table["guest_labels"], "podcast.guest_labels"),
            sample_line=table["sample_line"],
        )

    def _check_table(self, table: dict[str, Any], schema: Mapping[str, type], where: str) -> None:
        for key in table.keys() - schema.keys():
            raise self._error(f"unknown key '{where}{key}'")
        for key, expected in schema.items():
            if key not in table:
                raise self._error(f"missing key '{where}{key}'")
            if not _has_type(table[key], expected):
                raise self._error(f"key '{where}{key}' must be {expected.__name__}")

    def _strings(self, values: Any, key: str) -> tuple[str, ...]:
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise self._error(f"key '{key}' must be a list of strings")
        return tuple(values)

    def _error(self, message: str) -> LanguageDataError:
        return LanguageDataError(f"{self._path.name}: {message}")


def _has_type(value: Any, expected: type) -> bool:
    if expected is int and isinstance(value, bool):
        return False
    return isinstance(value, expected)


def _check_across_files(records: tuple[LanguageRecord, ...]) -> None:
    _refuse_duplicates("code", (record.code for record in records))
    _refuse_duplicates("order", (record.order for record in records))
    _refuse_duplicates("voice key", (voice.key for record in records for voice in record.voices))


def _refuse_duplicates(what: str, values: Iterable[object]) -> None:
    duplicates = sorted(str(value) for value, count in Counter(values).items() if count > 1)
    if duplicates:
        raise LanguageDataError(f"{what} used by more than one language file: {duplicates}")
