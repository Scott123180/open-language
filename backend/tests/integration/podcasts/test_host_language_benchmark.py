"""SC-005: at least 95% of host lines are entirely in the episode's language, in both languages.

Hand-run against the real default model, deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k language

German lines are checked with 006's wordfreq test for English and Spanish words; Spanish lines
with 005's list of English function words. The table is printed before the assertion runs.
"""

import pytest

from tests.integration.conversation_levels.text_metrics import native_language_words
from tests.integration.podcasts.podcast_harness import real_podcast_app
from tests.integration.practice_languages.text_purity import foreign_words

pytestmark = pytest.mark.benchmark

SC_005_MIN_PURE_SHARE = 0.95
EPISODES = (("one_host", 0), ("one_host", 1), ("one_host", 2), ("panel", 3), ("panel", 4))
LEARNER_TURNS = 5
CHECKERS = {"es": native_language_words, "de": foreign_words}


@pytest.mark.parametrize("language", ["es", "de"])
def test_host_lines_stay_in_the_episodes_language(tmp_path, language):
    with real_podcast_app(tmp_path, language) as harness:
        lines = [
            line["content"]
            for format, show in EPISODES
            for line in harness.run_episode(format, show, LEARNER_TURNS).host_lines
        ]
    flagged = [(text, CHECKERS[language](text)) for text in lines if CHECKERS[language](text)]
    pure_share = 1 - len(flagged) / len(lines)
    print(  # noqa: T201
        f"\nSC-005 {language}: {len(lines)} host lines, {len(flagged)} flagged, {pure_share:.1%} pure"
    )
    for text, words in flagged:
        print(f"  flagged {words}: {text}")  # noqa: T201
    assert pure_share >= SC_005_MIN_PURE_SHARE
