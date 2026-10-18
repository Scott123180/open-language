"""SC-002, SC-003: do the hosts recall an earlier point, and choose a new topic? (research R12)

Hand-run against the real default model, deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k series_recall

Twenty two-episode series, each on its own scratch database. In episode 1 the learner states
two known facts, then the episode ends and the hosts catch up, as a Start would wait for. Episode
2 runs to ten host lines. Each series is written to `series-review-sheet.md` with the facts, what
the hosts remember, and episode 2's lines; the reviewer fills the three judgement columns.
"""

import pytest

from tests.integration.podcasts.podcast_harness import real_podcast_app
from tests.integration.podcasts.series_benchmark import (
    end,
    play,
    remembered,
    show_ids,
    start_series,
    wait_for_memory,
    write_sheet,
)

pytestmark = pytest.mark.benchmark

SERIES_COUNT = 20
EPISODE_TWO_HOST_LINES = 10
EPISODE_ONE_HOST_LINES = 8
KNOWN_FACTS = (
    (
        "Odio las mañanas, siempre llego tarde al trabajo.",
        "Este fin de semana voy a la playa con mi hermana.",
    ),
    ("Tengo un perro que se llama Toby.", "Mañana empiezo un curso de cocina."),
    ("Vivo en Manchester desde hace tres años.", "Mi deporte favorito es el baloncesto."),
    ("Trabajo como enfermera en un hospital.", "El verano pasado viajé a Portugal."),
    ("Toco la guitarra todos los domingos.", "No me gusta nada el café."),
)
INSTRUCTIONS = (
    "For each series: **Refers back** = some episode-2 host line correctly mentions a specific "
    "point from episode 1 (SC-002, bar ≥ 16/20); **Invented** = a host presents a memory that "
    "was never said (SC-002, bar 0); **New topic** = episode 2's subject is not a remembered "
    "topic (SC-003, bar ≥ 18/20)."
)


def _series_section(
    index: int, show_id: str, facts, memory: dict, lines: list[str], outcome
) -> list[str]:
    topics = "; ".join(point["text"] for point in memory["topics"]) or "—"
    learner = "; ".join(point["text"] for point in memory["about_learner"]) or "—"
    numbered = [f"{n}. {line}" for n, line in enumerate(lines, start=1)]
    return [
        f"### Series {index}: {show_id}",
        "",
        f"- Facts said in episode 1: {' / '.join(facts)}",
        f"- Catch-up before episode 2: {outcome['status']}",
        f"- Remembered topics: {topics}",
        f"- Remembered about the learner: {learner}",
        "- Episode 2 host lines:",
        "",
        *(f"  {line}" for line in numbered),
        "",
        "| Refers back | Invented | New topic | Note |",
        "|---|---|---|---|",
        "|  |  |  |  |",
        "",
    ]


def _run_series(tmp_path, index: int) -> list[str]:
    show_id = show_ids()[index % len(show_ids())]
    facts = KNOWN_FACTS[index % len(KNOWN_FACTS)]
    with real_podcast_app(tmp_path / f"series-{index}", "es") as harness:
        first = start_series(harness.client, show_id, "one_host")
        play(harness.client, first["conversation_id"], list(facts), EPISODE_ONE_HOST_LINES)
        end(harness.client, first["conversation_id"])
        outcome, _seconds = wait_for_memory(harness.client, first["series"]["series_id"])
        memory = remembered(harness.client, first["series"]["series_id"])
        second = start_series(harness.client, show_id, "one_host")
        lines = play(
            harness.client, second["conversation_id"], [], EPISODE_TWO_HOST_LINES
        ).host_lines
    return _series_section(index + 1, show_id, facts, memory, lines, outcome)


def test_write_twenty_second_episodes_for_review(tmp_path):
    sections = [line for index in range(SERIES_COUNT) for line in _run_series(tmp_path, index)]

    write_sheet("SC-002 / SC-003: recall and new topics", [INSTRUCTIONS, "", *sections])
    assert sections
