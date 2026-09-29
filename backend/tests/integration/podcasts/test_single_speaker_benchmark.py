"""SC-003: across 10 Listen and 10 Panel episodes, no host line holds another speaker's speech.

Hand-run against the real default model, deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k single_speaker

Every stored line is checked for another participant's label (the other host, the learner, a role
word or the language's guest labels), and the sanitiser's `was_trimmed` rate is printed, so SC-003
can be audited from the database (research R4).
"""

import re

import pytest

from app.practice_languages import guest_labels_for
from tests.integration.podcasts.podcast_harness import RunResult, real_podcast_app

pytestmark = pytest.mark.benchmark

EPISODES_PER_FORMAT = 10
LEARNER_TURNS = 5
ROLE_WORDS = ("Guest", "Learner", "User", "You")


def _leaks(run: RunResult, language: str) -> list[str]:
    names = {host["host_id"]: host["name"] for host in run.hosts}
    leaked = []
    for line in run.host_lines:
        others = [name for host_id, name in names.items() if host_id != line["host_id"]]
        labels = (*others, *ROLE_WORDS, *guest_labels_for(language))
        pattern = rf"(^|[.!?\n]\s*)\W{{0,2}}({'|'.join(map(re.escape, labels))})\W{{0,2}}\s*:"
        if re.search(pattern, line["content"], re.IGNORECASE):
            leaked.append(line["content"])
    return leaked


@pytest.mark.parametrize("format", ["listen", "panel"])
def test_no_host_line_speaks_for_anyone_else(tmp_path, format):
    with real_podcast_app(tmp_path, "es") as harness:
        runs = [
            harness.run_episode(format, index, LEARNER_TURNS)
            for index in range(EPISODES_PER_FORMAT)
        ]
        trimmed = sum(harness.trimmed_count(run) for run in runs)
    leaks = [text for run in runs for text in _leaks(run, "es")]
    total = sum(len(run.host_lines) for run in runs)
    print(  # noqa: T201
        f"\nSC-003 {format}: {total} host lines, {len(leaks)} with another speaker, "
        f"{trimmed} trimmed ({trimmed / total:.1%})"
    )
    for text in leaks:
        print(f"  leaked: {text}")  # noqa: T201
    assert leaks == []
