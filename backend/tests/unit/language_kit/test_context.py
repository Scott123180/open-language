"""T026: the app facts rules read, gathered once per command."""

import faster_whisper.tokenizer
import wordfreq

from language_kit.context import gather_rule_context
from language_kit.workspace import Workspace
from tests.unit.language_kit.conftest import SCENARIO_IDS


def test_the_context_holds_the_scenario_ids_from_the_scenario_provider(workspace: Workspace):
    assert gather_rule_context(workspace).scenario_ids == SCENARIO_IDS


def test_catalogued_codes_are_the_workspace_data_files(workspace: Workspace):
    (workspace.runtime_dir / "es.toml").unlink()

    assert gather_rule_context(workspace).catalogued_codes == frozenset({"de"})


def test_explanation_codes_come_from_the_native_language_names(workspace: Workspace):
    assert gather_rule_context(workspace).explanation_codes == frozenset({"en"})


def test_whisper_and_wordfreq_codes_cover_the_practice_languages(workspace: Workspace):
    context = gather_rule_context(workspace)

    assert {"es", "de", "it"} <= context.whisper_codes
    assert {"es", "de", "it"} <= context.wordfreq_codes


def test_the_voice_catalogue_is_absent_unless_given(workspace: Workspace):
    assert gather_rule_context(workspace).voice_catalogue is None


def test_faster_whisper_still_exposes_its_language_codes():
    """Pins a private name (plan Complexity Tracking): an upgrade that moves it fails here."""
    assert {"es", "de", "it"} <= set(faster_whisper.tokenizer._LANGUAGE_CODES)


def test_wordfreq_covers_the_practice_languages():
    assert {"es", "de", "it"} <= set(wordfreq.available_languages())
