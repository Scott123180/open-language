"""T047: a new per-language requirement, end to end (US4 scenarios 1-3; quickstart §8 automated)."""

import difflib
import tomllib

from language_kit.cli import EXIT_FINDINGS, EXIT_OK
from language_kit.registry import REQUIREMENTS, Destination, Producer, Requirement
from language_kit.rules import Required
from tests.unit.language_kit.conftest import (
    CATALOGUED_VOICES,
    install_voices,
    make_kit,
    run_kit,
    write_valid_evaluation,
)

GREETING = Requirement(
    "podcast.example_only_field",
    Destination.RUNTIME,
    Producer.AGENT,
    "009",
    "How a host opens an episode.",
    (Required(),),
)
GREETINGS = {"es": "¡Hola a todos!", "de": "Hallo zusammen!"}


def _failing_paths(output: str) -> set[tuple[str, str]]:
    return {tuple(line.split()[1:3]) for line in output.splitlines() if line.startswith("FAIL")}


def test_a_new_requirement_is_backfilled_line_by_line(workspace):
    write_valid_evaluation(workspace, "es")
    install_voices(workspace, *CATALOGUED_VOICES)
    kit = make_kit(workspace, requirements=(*REQUIREMENTS, GREETING))
    before = {
        code: (workspace.runtime_dir / f"{code}.toml").read_text(encoding="utf-8")
        for code in GREETINGS
    }

    code, output = run_kit(kit, "check", "--all")
    assert code == EXIT_FINDINGS
    assert _failing_paths(output) == {
        ("es", "podcast.example_only_field:"),
        ("de", "podcast.example_only_field:"),
    }

    run_kit(kit, "backfill", "--all")
    for language, greeting in GREETINGS.items():
        pack = workspace.language_dir(language) / "backfill-pack.toml"
        text = pack.read_text(encoding="utf-8")
        assert tomllib.loads(text) == {"code": language, "podcast": {"example_only_field": "TODO"}}
        pack.write_text(
            text.replace('example_only_field = "TODO"', f'example_only_field = "{greeting}"'),
            encoding="utf-8",
        )
        assert run_kit(kit, "apply", language, "--pack", str(pack))[0] == EXIT_OK

    for language, greeting in GREETINGS.items():
        after = (workspace.runtime_dir / f"{language}.toml").read_text(encoding="utf-8")
        diff = [
            line
            for line in difflib.ndiff(before[language].splitlines(), after.splitlines())
            if line[:1] in "+-"
        ]
        assert diff == [f'+ example_only_field = "{greeting}"']
    assert run_kit(kit, "check", "--all")[0] == EXIT_OK
