"""The app facts rules read, gathered once per command. Rules never import the app themselves."""

from dataclasses import dataclass, field, replace

import faster_whisper.tokenizer
import wordfreq

from app.practice_languages import NATIVE_LANGUAGE_NAMES
from app.services.factory import get_scenario_provider
from language_kit.language_files import LanguageData
from language_kit.voices import VoiceCatalogue
from language_kit.workspace import Workspace


@dataclass(frozen=True, slots=True)
class RuleContext:
    scenario_ids: tuple[str, ...]
    catalogued_codes: frozenset[str]
    explanation_codes: frozenset[str]
    whisper_codes: frozenset[str]
    wordfreq_codes: frozenset[str]
    voice_catalogue: VoiceCatalogue | None = None
    code: str = ""
    """The language being checked."""
    path: str = ""
    """The registry path being checked."""
    language: LanguageData = field(default_factory=lambda: LanguageData("", {}))
    """All of the language's values, for rules that compare items."""
    others: tuple[LanguageData, ...] = ()
    """The other catalogued languages, for rules about uniqueness across languages."""

    def for_language(
        self, language: LanguageData, others: tuple[LanguageData, ...]
    ) -> "RuleContext":
        return replace(self, code=language.code, language=language, others=others)

    def at(self, path: str) -> "RuleContext":
        return replace(self, path=path)

    def with_catalogue(self, catalogue: VoiceCatalogue) -> "RuleContext":
        return replace(self, voice_catalogue=catalogue)


def gather_rule_context(workspace: Workspace) -> RuleContext:
    return RuleContext(
        scenario_ids=tuple(scenario.id for scenario in get_scenario_provider().get_all()),
        catalogued_codes=frozenset(path.stem for path in workspace.runtime_dir.glob("*.toml")),
        explanation_codes=frozenset(NATIVE_LANGUAGE_NAMES),
        whisper_codes=frozenset(faster_whisper.tokenizer._LANGUAGE_CODES),
        wordfreq_codes=frozenset(wordfreq.available_languages()),
    )
