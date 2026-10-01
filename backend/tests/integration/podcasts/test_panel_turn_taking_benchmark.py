"""SC-002: across 10 Panel episodes of 10 learner turns, the learner is invited within four host
lines, and each host speaks at least 25% of the host lines in every episode.

Hand-run against the real default model, deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k panel_turn_taking

The turn policy decides who speaks and when the learner is invited, so the spacing and the share
are asserted. Whether an inviting line really addresses the learner is the model's part: a line
marked `invites_learner` with no question in it is printed for a human check (research R3).
"""

import pytest

from tests.integration.podcasts.podcast_harness import RunResult, real_podcast_app

pytestmark = pytest.mark.benchmark

EPISODES = 10
LEARNER_TURNS = 10
MAX_LINES_BEFORE_INVITE = 4
MIN_HOST_SHARE = 0.25
QUESTION_MARKS = ("?", "¿")


def _longest_wait(run: RunResult) -> int:
    """The most host lines the learner heard before one of them invited the learner in."""
    longest, waiting = 0, 0
    for line in run.lines:
        waiting = 0 if line["speaker"] == "learner" else waiting + 1
        longest = max(longest, waiting)
        waiting = 0 if line["invites_learner"] else waiting
    return longest


def _smallest_share(run: RunResult) -> float:
    lines = run.host_lines
    counts = [sum(line["host_id"] == host["host_id"] for line in lines) for host in run.hosts]
    return min(counts) / len(lines)


def _unaddressed_invitations(run: RunResult) -> list[str]:
    return [
        line["content"]
        for line in run.host_lines
        if line["invites_learner"] and not any(mark in line["content"] for mark in QUESTION_MARKS)
    ]


def test_the_learner_is_invited_often_and_both_hosts_share_the_floor(tmp_path):
    with real_podcast_app(tmp_path, "es") as harness:
        runs = [harness.run_episode("panel", index, LEARNER_TURNS) for index in range(EPISODES)]
    waits = [_longest_wait(run) for run in runs]
    shares = [_smallest_share(run) for run in runs]
    flagged = [text for run in runs for text in _unaddressed_invitations(run)]
    print(f"\nSC-002: longest waits {waits}, smallest host shares {shares}")  # noqa: T201
    for text in flagged:
        print(f"  check (invites, no question): {text}")  # noqa: T201
    assert max(waits) <= MAX_LINES_BEFORE_INVITE
    assert min(shares) >= MIN_HOST_SHARE
