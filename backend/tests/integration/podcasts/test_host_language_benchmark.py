"""SC-005: at least 95% of host lines are entirely in the episode's language, in every language.

Hand-run against the real default model, deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k language

Spanish lines are checked with 005's list of English function words; every other language with
the wordfreq test for words of English and the other practice languages (008, research R8). The table is printed before the assertion runs.
"""

import pytest

from app.practice_languages import DEFAULT_PRACTICE_LANGUAGE, PRACTICE_LANGUAGES
from tests.integration.conversation_levels.text_metrics import native_language_words
from tests.integration.podcasts.podcast_harness import real_podcast_app
from tests.integration.practice_languages.text_purity import foreign_words, other_languages

pytestmark = pytest.mark.benchmark

SC_005_MIN_PURE_SHARE = 0.95
EPISODES = (("one_host", 0), ("one_host", 1), ("one_host", 2), ("panel", 3), ("panel", 4))
LEARNER_TURNS = 5


def _other_language_words(language: str):
    """Spanish keeps 005's English-word check; any other language uses the generalised one."""
    if language == DEFAULT_PRACTICE_LANGUAGE:
        return native_language_words
    return lambda text: foreign_words(text, language, other_languages(language))


@pytest.mark.parametrize("language", list(PRACTICE_LANGUAGES))
def test_host_lines_stay_in_the_episodes_language(tmp_path, language):
    with real_podcast_app(tmp_path, language) as harness:
        lines = [
            line["content"]
            for format, show in EPISODES
            for line in harness.run_episode(format, show, LEARNER_TURNS).host_lines
        ]
    checker = _other_language_words(language)
    flagged = [(text, checker(text)) for text in lines if checker(text)]
    pure_share = 1 - len(flagged) / len(lines)
    print(  # noqa: T201
        f"\nSC-005 {language}: {len(lines)} host lines, {len(flagged)} flagged, {pure_share:.1%} pure"
    )
    for text, words in flagged:
        print(f"  flagged {words}: {text}")  # noqa: T201
    assert pure_share >= SC_005_MIN_PURE_SHARE
