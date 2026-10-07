"""T028: where the kit finds the repository, the data and its output."""

from pathlib import Path

import pytest

from language_kit.workspace import KitUsageError, Workspace


def test_the_root_is_found_from_a_directory_inside_it(repo: Path):
    assert Workspace.discover(repo / "backend", environ={}).root == repo


def test_the_data_directories_sit_under_the_root(repo: Path):
    workspace = Workspace.discover(repo, environ={})

    assert workspace.runtime_dir == repo / "backend/app/language_data/languages"
    assert (
        workspace.evaluation_dir == repo / "backend/tests/integration/practice_languages/evaluation"
    )


def test_the_output_root_defaults_to_the_feature_directory(repo: Path):
    workspace = Workspace.discover(repo, environ={})

    assert workspace.output_root == repo / "specs/008-language-onboarding-kit/languages"
    assert workspace.language_dir("it") == workspace.output_root / "it"


def test_out_overrides_the_output_root(repo: Path, tmp_path: Path):
    assert Workspace.discover(repo, out=tmp_path, environ={}).output_root == tmp_path


def test_without_a_feature_file_out_is_required(repo: Path):
    (repo / ".specify/feature.json").unlink()

    with pytest.raises(KitUsageError, match="--out"):
        Workspace.discover(repo, environ={}).output_root  # noqa: B018


def test_the_voice_directory_follows_the_environment(repo: Path, tmp_path: Path):
    workspace = Workspace.discover(repo, environ={"OPEN_LANGUAGE_VOICE_DIR": str(tmp_path)})

    assert workspace.voice_dir == tmp_path


def test_the_voice_directory_defaults_to_the_piper_voices_folder(repo: Path):
    assert (
        Workspace.discover(repo, environ={}).voice_dir == Path.home() / ".local/share/piper-voices"
    )


def test_a_directory_outside_any_repository_is_a_usage_error(tmp_path: Path):
    with pytest.raises(KitUsageError):
        Workspace.discover(tmp_path, environ={})


def test_relative_paths_are_shown_from_the_root(repo: Path):
    workspace = Workspace.discover(repo, environ={})

    assert (
        workspace.relative(workspace.runtime_dir / "it.toml")
        == "backend/app/language_data/languages/it.toml"
    )


def test_a_relative_path_is_found_from_the_callers_directory(repo: Path):
    (repo / "backend" / "pack.toml").write_text("", encoding="utf-8")
    workspace = Workspace.discover(repo, environ={"LANGUAGE_KIT_CWD": str(repo / "backend")})

    assert workspace.resolve(Path("pack.toml")) == repo / "backend" / "pack.toml"


def test_a_relative_path_is_otherwise_taken_from_the_root(repo: Path):
    workspace = Workspace.discover(repo, environ={"LANGUAGE_KIT_CWD": str(repo / "backend")})

    assert workspace.resolve(Path("specs/x/pack.toml")) == repo / "specs/x/pack.toml"


def test_an_absolute_path_is_kept(repo: Path, tmp_path: Path):
    assert Workspace.discover(repo, environ={}).resolve(tmp_path) == tmp_path
