"""Reading a pack and checking it against a language's data: shared by validate, apply and finish."""

from dataclasses import dataclass
from pathlib import Path

from language_kit.checking import catalogued_languages, others_than
from language_kit.composition import Kit
from language_kit.errors import KitUsageError
from language_kit.findings import Finding
from language_kit.language_files import LanguageData
from language_kit.pack import LanguagePack

PACK_FILE = "pack.toml"


@dataclass(frozen=True, slots=True)
class PackCheck:
    pack: LanguagePack
    path: Path
    existing: LanguageData | None
    """The language's current data; None for a language not yet catalogued."""
    others: tuple[LanguageData, ...]
    findings: list[Finding]

    @property
    def errors(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.is_error]

    @property
    def warnings(self) -> list[Finding]:
        return [finding for finding in self.findings if not finding.is_error]

    def added_voices(self) -> list[str]:
        """Voice keys the pack adds to the language."""
        current = {voice.get("key") for voice in _voices(self.existing)}
        return [
            str(voice["key"])
            for voice in _voices(self.pack.data)
            if voice.get("key") not in current
        ]


def pack_path(kit: Kit, code: str, given: Path | None) -> Path:
    return given if given is not None else kit.workspace.language_dir(code) / PACK_FILE


def check_pack(kit: Kit, code: str, given: Path | None) -> PackCheck:
    path = pack_path(kit, code, given)
    if not path.is_file():
        relative = kit.workspace.relative(path)
        raise KitUsageError(
            f"no pack at {relative}: run kit.sh scaffold {code} --name <Name> first"
        )
    pack = LanguagePack.parse(path.read_text(encoding="utf-8"), code, kit.requirements)
    languages = catalogued_languages(kit.workspace)
    existing, others = languages.get(code), others_than(code, languages)
    partial = PackCheck(pack, path, existing, others, [])
    context = kit.rule_context()
    if partial.added_voices() and kit.voice_catalogue is not None:
        context = context.with_catalogue(kit.voice_catalogue)
    findings = pack.findings(context, others, existing, onboarding=existing is None)
    return PackCheck(pack, path, existing, others, findings)


def _voices(language: LanguageData | None) -> list[dict[str, object]]:
    voices = language.get("voices") if language is not None else None
    return [voice for voice in voices or [] if isinstance(voice, dict)]
