"""T043: `apply` validates, fetches voices first, then writes both files atomically (research R9)."""

import os

import pytest

import language_kit.apply as apply_module
from language_kit.cli import EXIT_EXTERNAL, EXIT_FINDINGS, EXIT_OK, EXIT_USAGE
from tests.unit.language_kit.conftest import (
    CATALOGUED_VOICES,
    install_voices,
    italian_catalogue,
    italian_pack_text,
    make_kit,
    run_kit,
    snapshot,
    write_valid_evaluation,
)
from tests.unit.language_kit.fakes import FakeVoiceDownloader


@pytest.fixture
def italian(workspace, tmp_path):
    """A kit with every catalogued voice installed and a complete Italian pack written."""
    install_voices(workspace, *CATALOGUED_VOICES)
    pack = tmp_path / "pack.toml"
    pack.write_text(italian_pack_text(), encoding="utf-8")
    downloader = FakeVoiceDownloader(workspace.voice_dir)
    kit = make_kit(workspace, voice_catalogue=italian_catalogue(), downloader=downloader)
    return kit, pack


def _repository(kit) -> dict[str, bytes]:
    return snapshot(kit.workspace.root)


def _spanish_pack(kit, tmp_path, body: str):
    """A partial Spanish pack; Spanish first gets a valid evaluation set so only the pack matters."""
    write_valid_evaluation(kit.workspace, "es")
    pack = tmp_path / "es-pack.toml"
    pack.write_text(f'code = "es"\n{body}', encoding="utf-8")
    return pack


def test_apply_writes_the_two_files_of_a_new_language(italian):
    kit, pack = italian

    code, output = run_kit(kit, "apply", "it", "--pack", str(pack))

    assert code == EXIT_OK
    assert (kit.workspace.runtime_dir / "it.toml").is_file()
    assert (kit.workspace.evaluation_dir / "it.toml").is_file()
    assert output.startswith("apply it: wrote 2 files, downloaded 2 voices")


def test_validation_errors_stop_before_anything_changes(italian, tmp_path):
    kit, _ = italian
    pack = tmp_path / "bad.toml"
    pack.write_text(italian_pack_text(name=""), encoding="utf-8")
    before = _repository(kit)

    code, output = run_kit(kit, "apply", "it", "--pack", str(pack))

    assert code == EXIT_FINDINGS
    assert "FAIL it name" in output
    assert _repository(kit) == before and kit.downloader.ensured == []


def test_voices_are_fetched_before_any_file_is_written(italian):
    kit, pack = italian
    target = kit.workspace.runtime_dir / "it.toml"
    seen = []
    kit.downloader = FakeVoiceDownloader(
        kit.workspace.voice_dir, before=lambda voice: seen.append(target.exists())
    )

    run_kit(kit, "apply", "it", "--pack", str(pack))

    assert seen == [False, False]


def test_added_voices_are_ensured_even_when_installed_so_their_checksums_are_verified(italian):
    kit, pack = italian
    install_voices(kit.workspace, "it_IT-paola-medium")

    run_kit(kit, "apply", "it", "--pack", str(pack))

    assert kit.downloader.ensured == ["it_IT-paola-medium", "it_IT-riccardo-x_low"]


def test_an_existing_voice_missing_from_the_voice_directory_is_fetched(italian, tmp_path):
    kit, _ = italian
    (kit.workspace.voice_dir / "es_AR-daniela-high.onnx").unlink()
    pack = _spanish_pack(kit, tmp_path, '[podcast]\nsample_line = "¡Hola, soy {name}!"\n')

    run_kit(kit, "apply", "es", "--pack", str(pack))

    assert kit.downloader.ensured == ["es_AR-daniela-high"]


def test_a_pack_that_changes_no_voice_touches_neither_catalogue_nor_network(italian, tmp_path):
    kit, _ = italian
    pack = _spanish_pack(kit, tmp_path, '[podcast]\nsample_line = "¡Hola, soy {name}!"\n')

    code, _ = run_kit(kit, "apply", "es", "--pack", str(pack))

    assert code == EXIT_OK
    assert kit.voice_catalogue.calls == 0 and kit.downloader.ensured == []


def test_a_download_failure_leaves_the_repository_untouched(italian):
    kit, pack = italian
    kit.downloader = FakeVoiceDownloader(kit.workspace.voice_dir, failing={"it_IT-riccardo-x_low"})
    before = _repository(kit)

    code, output = run_kit(kit, "apply", "it", "--pack", str(pack))

    assert code == EXIT_EXTERNAL
    assert "it_IT-riccardo-x_low" in output
    assert _repository(kit) == before


def test_a_failed_second_replace_restores_the_first_file(italian, tmp_path, monkeypatch):
    kit, _ = italian
    body = '[podcast]\nsample_line = "¡Hola, soy {name}!"\n[evaluation]\nloanwords = ["ok"]\n'
    pack = _spanish_pack(kit, tmp_path, body)
    before = _repository(kit)
    calls = []

    def flaky_replace(source, target):
        calls.append(target)
        if len(calls) == 2:
            raise OSError("disk full")
        os.replace(source, target)

    monkeypatch.setattr(apply_module.os, "replace", flaky_replace)

    code, _ = run_kit(kit, "apply", "es", "--pack", str(pack))

    assert code == EXIT_EXTERNAL
    assert _repository(kit) == before
    assert not list(kit.workspace.runtime_dir.glob("*.tmp")) and not list(
        kit.workspace.evaluation_dir.glob("*.tmp")
    )


def test_applying_the_same_pack_again_is_nothing_to_do(italian):
    kit, pack = italian
    run_kit(kit, "apply", "it", "--pack", str(pack))
    before = _repository(kit)

    code, output = run_kit(kit, "apply", "it", "--pack", str(pack))

    assert code == EXIT_OK
    assert output.startswith("apply it: nothing-to-do")
    assert _repository(kit) == before


def test_a_dry_run_reports_and_changes_nothing(italian):
    kit, pack = italian
    before = _repository(kit)

    code, output = run_kit(kit, "apply", "it", "--pack", str(pack), "--dry-run")

    assert code == EXIT_OK
    assert "would write backend/app/language_data/languages/it.toml (+" in output
    assert "would download it_IT-paola-medium (60 MB)" in output
    assert _repository(kit) == before and kit.downloader.ensured == []


def test_a_partial_pack_changes_only_its_item(italian, tmp_path):
    kit, _ = italian
    runtime = kit.workspace.runtime_dir / "es.toml"
    old = runtime.read_text(encoding="utf-8")
    pack = _spanish_pack(kit, tmp_path, '[podcast]\nsample_line = "¡Hola, soy {name}!"\n')

    run_kit(kit, "apply", "es", "--pack", str(pack))

    new = runtime.read_text(encoding="utf-8")
    changed = [(a, b) for a, b in zip(old.splitlines(), new.splitlines(), strict=True) if a != b]
    assert changed == [
        (
            'sample_line = "Hola, soy {name}. ¡Bienvenidos al programa!"',
            'sample_line = "¡Hola, soy {name}!"',
        )
    ]


def test_no_other_language_changes(italian):
    kit, pack = italian
    others = snapshot(kit.workspace.runtime_dir) | snapshot(kit.workspace.evaluation_dir)

    run_kit(kit, "apply", "it", "--pack", str(pack))

    after = snapshot(kit.workspace.runtime_dir) | snapshot(kit.workspace.evaluation_dir)
    assert {path: after[path] for path in others} == others


def test_a_missing_pack_is_a_usage_error(italian):
    kit, _ = italian

    code, output = run_kit(kit, "apply", "it")

    assert code == EXIT_USAGE
    assert "kit.sh scaffold it --name" in output


def test_a_missing_voice_without_a_downloader_is_an_external_failure(workspace, tmp_path):
    pack = tmp_path / "pack.toml"
    pack.write_text(italian_pack_text(), encoding="utf-8")
    kit = make_kit(workspace, voice_catalogue=italian_catalogue())

    assert run_kit(kit, "apply", "it", "--pack", str(pack))[0] == EXIT_EXTERNAL


def test_a_failed_second_replace_removes_a_new_languages_first_file(italian, monkeypatch):
    kit, pack = italian
    before = _repository(kit)
    calls = []

    def flaky_replace(source, target):
        calls.append(target)
        if len(calls) == 2:
            raise OSError("disk full")
        os.replace(source, target)

    monkeypatch.setattr(apply_module.os, "replace", flaky_replace)

    assert run_kit(kit, "apply", "it", "--pack", str(pack))[0] == EXIT_EXTERNAL
    assert _repository(kit) == before


def test_a_dry_run_says_an_installed_added_voice_would_be_verified(italian):
    kit, pack = italian
    install_voices(kit.workspace, "it_IT-paola-medium")

    _, output = run_kit(kit, "apply", "it", "--pack", str(pack), "--dry-run")

    assert "would verify it_IT-paola-medium (installed)" in output
