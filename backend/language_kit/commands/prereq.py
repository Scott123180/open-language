"""`prereq <code>`: read-only (apart from the voice-catalogue cache); can this language be onboarded?"""

import argparse

from language_kit.commands.base import Command
from language_kit.composition import Kit
from language_kit.errors import KitExternalError
from language_kit.output import EXIT_OK, EXIT_USAGE, CommandResult
from language_kit.prerequisites import Prerequisites, check_prerequisites
from language_kit.voices import VoiceCandidate, VoiceCatalogue

MEGABYTE = 1_000_000


class PrereqCommand(Command):
    name = "prereq"
    help = "read-only: check a language can be onboarded and list its voices"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("code", help="the ISO 639-1 code of the language to add")

    def run(self, arguments: argparse.Namespace, kit: Kit) -> CommandResult:
        return prerequisites_result(prerequisites(kit, arguments.code))


def prerequisites(kit: Kit, code: str) -> Prerequisites:
    return check_prerequisites(code, kit.rule_context(), _catalogue(kit))


def prerequisites_result(found: Prerequisites) -> CommandResult:
    if found.failure is not None:
        summary = f"prereq {found.code}: cannot be onboarded (check {found.passed + 1} of {found.total} failed)"
        return CommandResult("prereq", EXIT_USAGE, summary, [found.failure.text()])
    noun = "warning" if len(found.warnings) == 1 else "warnings"
    summary = (
        f"prereq {found.code}: {found.language_name} can be onboarded "
        f"({found.passed}/{found.total} checks, {len(found.warnings)} {noun})"
    )
    lines = [_voice_line(voice) for voice in found.candidates] + [w.text() for w in found.warnings]
    next_step = f"kit.sh scaffold {found.code} --name {found.language_name}"
    return CommandResult(
        "prereq", EXIT_OK, summary, lines, next_step, {"voices": [v.key for v in found.candidates]}
    )


def _voice_line(voice: VoiceCandidate) -> str:
    return f"voice {voice.key:<28} {voice.country:<12} {voice.quality:<7} {round(voice.size_bytes / MEGABYTE)} MB"


def _catalogue(kit: Kit) -> VoiceCatalogue:
    if kit.voice_catalogue is None:
        raise KitExternalError(
            "voice discovery needs the Piper voice catalogue, which is not configured"
        )
    return kit.voice_catalogue
