"""011 T128: guest episodes on the real model, for the SC-009 review (FR-020–FR-022, R10, R11).

Hand-run on the default local setup, deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k guest_episode

Each run is a fresh Panel series of Big Little Questions: episode 1 with the regular hosts, then
episode 2 with a guest in the second host's chair, then episode 3 with the regular host back. It
prints the guest episode's opening and the guest's introduction, and every episode-3 line that
speaks of the guest episode, so a reviewer can check that the guest is introduced as a guest,
the regular host is away rather than gone, and the returning host never claims to have been
there. `OPEN_LANGUAGE_BENCH_GUEST_RUNS` sets the runs (default 10); the report is written to
`OPEN_LANGUAGE_BENCH_REPORT` (default: the system temporary folder).
"""

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.integration.podcasts.podcast_harness import real_podcast_app
from tests.integration.podcasts.series_benchmark import (
    SERIES,
    end,
    play,
    start_series,
    wait_for_memory,
)
from tests.support.podcast_harness import EPISODES

pytestmark = pytest.mark.benchmark

SHOW_ID = "big-little-questions"
RUNS = int(os.environ.get("OPEN_LANGUAGE_BENCH_GUEST_RUNS", "10"))
REPORT = Path(os.environ.get("OPEN_LANGUAGE_BENCH_REPORT", tempfile.gettempdir())) / "guests.md"
HOST_LINES = 8
REPLIES = ["Me encantan las tostadas con tomate.", "¿Por qué se queman tan rápido?"]
SECONDHAND_WORDS = ("episodio", "la semana pasada", "la última vez", "me contaron", "me dijo")


@dataclass
class GuestRun:
    guest: str
    away: str
    opening: str
    introduction: str
    mentions: list[str]


def _guest(client, series_id: int) -> dict:
    body = {"language": "es", "slot": "second", "format": "panel", "learner_name": "Sam"}
    response = client.post(f"{SERIES}/{series_id}/guest", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _start_with(client, guest: dict) -> dict:
    show = next(
        s for s in client.get("/api/podcasts/catalog").json()["shows"] if s["show_id"] == SHOW_ID
    )
    body = {
        "show": show,
        "format": "panel",
        "length": "short",
        "kind": "series",
        "learner_name": "Sam",
    }
    response = client.post(EPISODES, json={**body, "guest": guest})
    assert response.status_code == 201, response.text
    return response.json()


def _played(client, episode: dict, series_id: int) -> dict:
    play(client, episode["conversation_id"], list(REPLIES), HOST_LINES)
    end(client, episode["conversation_id"])
    wait_for_memory(client, series_id)
    return client.get(f"{EPISODES}/{episode['conversation_id']}").json()


def _line_of(state: dict, is_guest: bool) -> str:
    hosts = {host["host_id"]: host for host in state["hosts"]}
    return next(
        (
            line["content"]
            for line in state["lines"]
            if line["host_id"] in hosts
            and hosts[line["host_id"]].get("is_guest", False) is is_guest
        ),
        "",
    )


def _mentions(state: dict, guest_name: str) -> list[str]:
    """Episode-3 host lines that speak of the guest or of an earlier episode."""
    return [
        line["content"]
        for line in state["lines"]
        if line["host_id"] is not None
        and (
            guest_name in line["content"]
            or any(w in line["content"].lower() for w in SECONDHAND_WORDS)
        )
    ]


def _run(tmp_path: Path, index: int) -> GuestRun:
    with real_podcast_app(tmp_path / f"guest-{index}", "es", "beginner") as harness:
        client = harness.client
        first = start_series(client, SHOW_ID, "panel")
        series_id = first["series"]["series_id"]
        _played(client, first, series_id)
        guest = _guest(client, series_id)
        guest_state = _played(client, _start_with(client, guest), series_id)
        after = _played(client, start_series(client, SHOW_ID, "panel"), series_id)
    return GuestRun(
        guest=guest["name"],
        away=guest_state["away_host_name"] or "",
        opening=_line_of(guest_state, is_guest=False),
        introduction=_line_of(guest_state, is_guest=True),
        mentions=_mentions(after, guest["name"]),
    )


def _write_report(runs: list[GuestRun]) -> None:
    lines = ["# Guest episode benchmark (SC-009)", ""]
    for number, run in enumerate(runs, start=1):
        lines += [
            f"## Run {number}: {run.guest} in for {run.away}",
            "",
            f"- Opening: {run.opening}",
        ]
        lines += [f"- Guest's introduction: {run.introduction}", "- Episode 3 mentions:"]
        lines += [f"  - {mention}" for mention in run.mentions] or ["  - (none)"]
        lines.append("")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines), f"\nReport: {REPORT}")  # noqa: T201


def test_guest_episodes_introduce_the_guest_and_the_host_comes_back(tmp_path):
    runs = [_run(tmp_path, index) for index in range(RUNS)]
    _write_report(runs)

    assert all(run.away for run in runs)
    assert all(run.introduction for run in runs)
