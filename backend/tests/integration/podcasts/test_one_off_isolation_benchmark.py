"""SC-004: one-off episodes of a show with a series never refer to earlier episodes (R12).

Hand-run against the real default model, deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k one_off_isolation

Each of twenty runs plays a series episode in which the learner states known facts, lets the
hosts catch up, then plays a one-off episode of the same show to ten host lines. A one-off's
prompt carries no memory, so any reference would be invented: every host line that mentions an
earlier episode or one of the facts is listed in `series-review-sheet.md` for review.
"""

import re

import pytest

from tests.integration.podcasts.podcast_harness import real_podcast_app
from tests.integration.podcasts.series_benchmark import (
    end,
    play,
    show_ids,
    start_one_off,
    start_series,
    wait_for_memory,
    write_sheet,
)

pytestmark = pytest.mark.benchmark

RUNS = 20
ONE_OFF_HOST_LINES = 10
FACTS = (
    "Odio las mañanas.",
    "Tengo un perro que se llama Toby.",
    "Este fin de semana voy a la playa.",
)
REFERENCE = re.compile(
    r"última vez|último episodio|episodio anterior|otro episodio|la otra vez|como (me )?dijiste|"
    r"recuerdas|mañanas|perro|toby|playa",
    re.IGNORECASE,
)
INSTRUCTIONS = (
    "Every one-off host line that mentions an earlier episode or a fact from the series. "
    "Mark each **Reference (Y/N)**: a Y is a line that refers to an earlier episode (SC-004, "
    'bar 0). A coincidental word ("mañanas" in a general sense) is an N.'
)


def _flagged(tmp_path, index: int) -> list[str]:
    show_id = show_ids()[index % len(show_ids())]
    with real_podcast_app(tmp_path / f"one-off-{index}", "es") as harness:
        series = start_series(harness.client, show_id, "one_host")
        play(harness.client, series["conversation_id"], list(FACTS), 6)
        end(harness.client, series["conversation_id"])
        wait_for_memory(harness.client, series["series"]["series_id"])
        one_off = start_one_off(harness.client, show_id, "one_host")
        lines = play(harness.client, one_off["conversation_id"], [], ONE_OFF_HOST_LINES).host_lines
    return [f"| {index + 1} | {show_id} | {line} |  |" for line in lines if REFERENCE.search(line)]


def test_list_one_off_lines_that_could_refer_back(tmp_path):
    rows = [row for index in range(RUNS) for row in _flagged(tmp_path, index)]

    table = ["| Run | Show | Host line | Reference (Y/N) |", "|---|---|---|---|", *rows]
    write_sheet(
        "SC-004: one-off isolation", [INSTRUCTIONS, "", f"Flagged lines: {len(rows)}", "", *table]
    )
    assert isinstance(rows, list)
