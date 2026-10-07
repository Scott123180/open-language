"""T041: canonical data files: fixed header, registry key order, tomli-w formatting, derived values."""

import pytest

from app.language_data import load_language_records
from language_kit.errors import KitUsageError
from language_kit.language_files import LanguageData, read_language
from language_kit.pack import LanguagePack
from language_kit.render import HEADER, derive, render
from language_kit.workspace import EVALUATION_DIR, RUNTIME_DIR, Workspace
from tests.unit.language_kit.conftest import (
    REPOSITORY,
    italian_catalogue,
    italian_pack_document,
    italian_pack_text,
)

COMMITTED = sorted(
    [*(REPOSITORY / RUNTIME_DIR).glob("*.toml"), *(REPOSITORY / EVALUATION_DIR).glob("*.toml")]
)


def _italian() -> LanguageData:
    return LanguagePack.parse(italian_pack_text(), "it").data


def _spanish_and_german(workspace: Workspace) -> list[LanguageData]:
    return [read_language("es", workspace), read_language("de", workspace)]


@pytest.mark.parametrize("path", COMMITTED, ids=lambda path: f"{path.parent.name}/{path.name}")
def test_rendering_a_committed_file_gives_the_same_bytes(path):
    workspace = Workspace(root=REPOSITORY, voice_dir=REPOSITORY)
    files = render(read_language(path.stem, workspace))

    expected = path.read_text(encoding="utf-8")
    assert (files.runtime if path.parent.name == "languages" else files.evaluation) == expected


def test_a_file_starts_with_the_generated_header():
    files = render(derive(_italian(), [], italian_catalogue()))

    assert files.runtime.startswith(HEADER.format(name="Italian", code="it"))
    assert files.evaluation.startswith(HEADER.format(name="Italian", code="it"))


def test_without_evaluation_values_there_is_no_evaluation_file(workspace):
    language = read_language("de", workspace).without("evaluation")

    assert render(language).evaluation is None


def test_the_evaluation_file_starts_with_the_code():
    evaluation = render(derive(_italian(), [], italian_catalogue())).evaluation

    assert evaluation.split("\n\n", 1)[1].startswith('code = "it"\nspecial_letters = "àèéìòù"\n')


def test_a_new_language_gets_the_next_order(workspace):
    derived = derive(_italian(), _spanish_and_german(workspace), italian_catalogue())

    assert derived.get("order") == 3


def test_a_new_voice_gets_its_name_locale_and_quality_from_the_catalogue():
    paola, riccardo = derive(_italian(), [], italian_catalogue()).get("voices")

    assert (paola["display_name"], paola["locale"], paola["quality"]) == (
        "Paola (Italy)",
        "it_IT",
        "medium",
    )
    assert riccardo["quality"] == "x_low"


def test_a_display_name_in_the_pack_is_kept():
    document = italian_pack_document()
    document["voices"][0]["display_name"] = "Paola (Roma)"

    paola, _ = derive(LanguageData("it", document), [], italian_catalogue()).get("voices")

    assert paola["display_name"] == "Paola (Roma)"


def test_existing_voices_keep_their_values_without_the_catalogue(workspace):
    catalogue = italian_catalogue()
    german = read_language("de", workspace)

    derived = derive(german, [], catalogue)

    assert derived.document == german.document
    assert catalogue.calls == 0


def test_a_voice_the_catalogue_lacks_cannot_be_derived():
    document = italian_pack_document()
    document["voices"] = [{"key": "it_IT-nobody-medium", "gender": "female"}]

    with pytest.raises(KitUsageError, match="it_IT-nobody-medium"):
        derive(LanguageData("it", document), [], italian_catalogue())


def test_a_new_voice_without_a_catalogue_cannot_be_derived():
    with pytest.raises(KitUsageError):
        derive(_italian(), [], None)


def test_rendered_files_load_in_the_app(workspace):
    derived = derive(_italian(), _spanish_and_german(workspace), italian_catalogue())
    (workspace.runtime_dir / "it.toml").write_text(render(derived).runtime, encoding="utf-8")

    records = load_language_records(workspace.runtime_dir)

    assert [record.code for record in records] == ["es", "de", "it"]
    assert records[2].voices[0].display_name == "Paola (Italy)"
