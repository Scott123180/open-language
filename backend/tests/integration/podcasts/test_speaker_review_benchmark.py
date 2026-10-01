"""SC-004: prints 10 episodes' host lines without their speakers, for the speaker review sheet.

Hand-run against the real default model and voices, deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k speaker_review

For each episode the hosts and their personalities are printed first, then every host line
numbered and unlabelled, then the answer key. The reviewer fills
`specs/007-podcast-mode/speaker-review-sheet.md` from the unlabelled lines (and the audio, from
the message ids) before reading the key.
"""

import pytest

from tests.integration.podcasts.podcast_harness import RunResult, real_podcast_app

pytestmark = pytest.mark.benchmark

EPISODES_PER_FORMAT = 5
LEARNER_TURNS = 3


def _print_for_review(index: int, run: RunResult) -> None:
    names = {host["host_id"]: host["name"] for host in run.hosts}
    cast = ", ".join(f"{host['name']} ({host['personality_label']})" for host in run.hosts)
    print(f"\nEpisode {index} — {cast}")  # noqa: T201
    for number, line in enumerate(run.host_lines, start=1):
        print(f"  {number}. [message {line['message_id']}] {line['content']}")  # noqa: T201
    key = ", ".join(f"{n}={names[line['host_id']]}" for n, line in enumerate(run.host_lines, 1))
    print(f"  Key: {key}")  # noqa: T201


@pytest.mark.parametrize("format", ["listen", "panel"])
def test_print_unlabelled_host_lines_for_review(tmp_path, format):
    with real_podcast_app(tmp_path, "es") as harness:
        runs = [
            harness.run_episode(format, index, LEARNER_TURNS, length="medium")
            for index in range(EPISODES_PER_FORMAT)
        ]
    for index, run in enumerate(runs, start=1):
        _print_for_review(index, run)
    assert all(len({line["host_id"] for line in run.host_lines}) == 2 for run in runs)
