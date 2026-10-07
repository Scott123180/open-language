"""T061: `finish` chains apply → verify → check → report, for full and backfill packs (FR-018, FR-027)."""

import json

import pytest

from language_kit.cli import EXIT_EXTERNAL, EXIT_FINDINGS, EXIT_OK
from tests.unit.language_kit.conftest import (
    CATALOGUED_VOICES,
    install_voices,
    italian_catalogue,
    italian_pack_text,
    make_kit,
    run_kit,
    snapshot,
)
from tests.unit.language_kit.fakes import FakeCommandRunner, FakeVoiceDownloader


@pytest.fixture
def kit(workspace):
    install_voices(workspace, *CATALOGUED_VOICES)
    return make_kit(
        workspace,
        voice_catalogue=italian_catalogue(),
        downloader=FakeVoiceDownloader(workspace.voice_dir),
        runner=FakeCommandRunner(),
    )


def _write_pack(kit, text: str, code: str = "it", name: str = "pack.toml"):
    path = kit.workspace.language_dir(code) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _commands(kit, code: str) -> list[str]:
    path = kit.workspace.language_dir(code) / "run-log.jsonl"
    return [json.loads(line)["command"] for line in path.read_text(encoding="utf-8").splitlines()]


def _report(kit, code: str):
    return kit.workspace.language_dir(code) / "report.md"


def test_finish_applies_verifies_checks_and_reports(kit):
    _write_pack(kit, italian_pack_text())

    code, output = run_kit(kit, "finish", "it")

    assert code == EXIT_OK
    assert output.splitlines()[0] == "finish it: apply ok, verify ok, check ok, report written"
    assert _commands(kit, "it") == ["apply", "verify", "check"]
    assert _report(kit, "it").is_file()
    assert (kit.workspace.runtime_dir / "it.toml").is_file()


def test_finish_applies_a_backfill_pack_and_reports_it(kit):
    body = '[evaluation]\nspecial_letters = ""\nloanwords = ["ok"]\n'
    body += "dictation = [" + ", ".join(f'"Frase número {n} aquí."' for n in range(20)) + "]\n"
    body += "[evaluation.turns]\n" + "".join(
        f'{s} = ["a.", "b.", "c.", "d.", "e."]\n' for s in kit.context.scenario_ids
    )
    pack = _write_pack(kit, f'code = "es"\n{body}', code="es", name="backfill-pack.toml")

    code, _ = run_kit(kit, "finish", "es", "--pack", str(pack))

    assert code == EXIT_OK
    assert (kit.workspace.evaluation_dir / "es.toml").is_file()
    assert _commands(kit, "es") == ["apply", "verify", "check"]
    assert "## Applied" in _report(kit, "es").read_text(encoding="utf-8")


def test_a_validation_error_stops_before_anything_is_written(kit):
    _write_pack(kit, italian_pack_text(name=""))
    before = snapshot(kit.workspace.root)

    code, output = run_kit(kit, "finish", "it")

    assert code == EXIT_FINDINGS
    assert "FAIL it name" in output
    assert snapshot(kit.workspace.root) == before
    assert kit.runner.calls == []


def test_a_failing_suite_stops_but_still_writes_the_report(workspace):
    install_voices(workspace, *CATALOGUED_VOICES)
    runner = FakeCommandRunner({"pytest": (1, "FAILED tests/a.py::test_b\n1 failed, 10 passed")})
    kit = make_kit(
        workspace,
        voice_catalogue=italian_catalogue(),
        downloader=FakeVoiceDownloader(workspace.voice_dir),
        runner=runner,
    )
    _write_pack(kit, italian_pack_text())

    code, output = run_kit(kit, "finish", "it")

    assert code == EXIT_EXTERNAL
    assert output.splitlines()[0] == "finish it: apply ok, verify failed, report written"
    assert _commands(kit, "it") == ["apply", "verify"]
    assert _report(kit, "it").is_file()


def test_a_download_failure_stops_and_still_writes_the_report(workspace):
    install_voices(workspace, *CATALOGUED_VOICES)
    downloader = FakeVoiceDownloader(workspace.voice_dir, failing={"it_IT-paola-medium"})
    kit = make_kit(
        workspace,
        voice_catalogue=italian_catalogue(),
        downloader=downloader,
        runner=FakeCommandRunner(),
    )
    _write_pack(kit, italian_pack_text())

    code, output = run_kit(kit, "finish", "it")

    assert code == EXIT_EXTERNAL
    assert "apply failed" in output.splitlines()[0]
    assert _report(kit, "it").is_file()
    assert not (kit.workspace.runtime_dir / "it.toml").exists()


def test_finishing_a_completed_language_again_only_verifies_and_reports(kit):
    _write_pack(kit, italian_pack_text())
    run_kit(kit, "finish", "it")
    data = snapshot(kit.workspace.runtime_dir, kit.workspace.evaluation_dir)

    code, output = run_kit(kit, "finish", "it")

    assert code == EXIT_OK
    assert (
        output.splitlines()[0]
        == "finish it: apply nothing-to-do, verify ok, check ok, report written"
    )
    assert snapshot(kit.workspace.runtime_dir, kit.workspace.evaluation_dir) == data


def test_backend_only_is_passed_to_verify(kit):
    _write_pack(kit, italian_pack_text())

    run_kit(kit, "finish", "it", "--backend-only")

    assert [name for name, *_ in kit.runner.calls] == ["pytest", "ruff", "black", "mypy"]
