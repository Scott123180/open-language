"""SC-006: at each level below Natural, host lines meet the level's limits at least as often as
roleplay partner replies do, with the same provider and model.

Hand-run against the real default model, deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k level

Uses 005's deterministic length measure. The table is printed before the assertion runs.
"""

import pytest

from app.conversation_levels import LEVEL_CATALOG, ConversationLevel
from tests.integration.conversation_levels.text_metrics import meets_length_limits
from tests.integration.podcasts.podcast_harness import real_podcast_app

pytestmark = pytest.mark.benchmark

LEVELS_BELOW_NATURAL = (
    ConversationLevel.BEGINNER,
    ConversationLevel.ELEMENTARY,
    ConversationLevel.INTERMEDIATE,
)
EPISODES = (("one_host", 0), ("panel", 1), ("panel", 2))
ROLEPLAY_SCENARIOS = ("order-at-restaurant", "buy-train-ticket", "check-into-hotel")
LEARNER_TURNS = 5


def _compliance(texts: list[str], level: ConversationLevel) -> float:
    limits = LEVEL_CATALOG[level].limits
    met = [
        meets_length_limits(text, limits.max_sentences_per_reply, limits.max_words_per_sentence)
        for text in texts
    ]
    return sum(met) / len(met)


@pytest.mark.parametrize("level", LEVELS_BELOW_NATURAL, ids=lambda level: level.value)
def test_host_lines_keep_to_the_level_as_well_as_roleplay(tmp_path, level):
    with real_podcast_app(tmp_path, "es", level.value) as harness:
        hosts = [
            line["content"]
            for format, show in EPISODES
            for line in harness.run_episode(format, show, LEARNER_TURNS).host_lines
        ]
        roleplay = [
            reply
            for scenario in ROLEPLAY_SCENARIOS
            for reply in harness.roleplay_replies(scenario, LEARNER_TURNS)
        ]
    host_rate, roleplay_rate = _compliance(hosts, level), _compliance(roleplay, level)
    print(  # noqa: T201
        f"\nSC-006 {level.value}: hosts {host_rate:.1%} of {len(hosts)}, "
        f"roleplay {roleplay_rate:.1%} of {len(roleplay)}"
    )
    assert host_rate >= roleplay_rate
