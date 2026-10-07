"""Can a language be onboarded at all? The checks of research R7, in order, using the libraries' lists."""

from dataclasses import dataclass

from language_kit.context import RuleContext
from language_kit.findings import Finding, Severity
from language_kit.language_files import LanguageData
from language_kit.registry import requirement
from language_kit.rules import Required, Rule
from language_kit.voices import VoiceCandidate, VoiceCatalogue

CODE_PATH = "code"


@dataclass(frozen=True, slots=True)
class Prerequisites:
    code: str
    passed: int
    total: int
    failure: Finding | None
    warnings: tuple[Finding, ...] = ()
    candidates: tuple[VoiceCandidate, ...] = ()

    @property
    def ok(self) -> bool:
        return self.failure is None

    @property
    def language_name(self) -> str:
        """The language's English name from the catalogue, or its code."""
        return next(
            (voice.language_name for voice in self.candidates if voice.language_name), self.code
        )


def check_prerequisites(
    code: str, context: RuleContext, catalogue: VoiceCatalogue
) -> Prerequisites:
    """Stop at the first failing check; a wordfreq gap or a single voice is only a warning."""
    rules = _code_rules()
    total = len(rules) + 1
    focused = context.for_language(LanguageData(code, {CODE_PATH: code}), ()).at(CODE_PATH)
    for index, rule in enumerate(rules):
        errors = [finding for finding in rule.check(code, focused) if finding.is_error]
        if errors:
            return Prerequisites(code, index, total, errors[0])
    candidates = catalogue.candidates(code)
    if not candidates:
        return Prerequisites(code, len(rules), total, _no_voice(code))
    return Prerequisites(code, total, total, None, _warnings(code, context, candidates), candidates)


def _code_rules() -> list[Rule]:
    """The code requirement's rules, minus `Required`: the code is given on the command line."""
    return [rule for rule in requirement(CODE_PATH).rules if not isinstance(rule, Required)]


def _no_voice(code: str) -> Finding:
    detail = f"The Piper catalogue has no single-speaker {code} voice the app can drive."
    return Finding(code, "voices", Severity.ERROR, "at least one single-speaker voice", detail)


def _warnings(
    code: str, context: RuleContext, candidates: tuple[VoiceCandidate, ...]
) -> tuple[Finding, ...]:
    warnings = []
    if code not in context.wordfreq_codes:
        detail = f'wordfreq has no {code}, so the adherence benchmark will be "not run".'
        warnings.append(
            Finding(
                code, "wordfreq", Severity.WARNING, "covered by the adherence word list", detail
            )
        )
    if len(candidates) == 1:
        detail = "Only one voice: podcasts will cast hosts of one gender only."
        warnings.append(Finding(code, "voices", Severity.WARNING, "voices of both genders", detail))
    return tuple(warnings)
