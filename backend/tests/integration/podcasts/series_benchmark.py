"""Shared steps for the hand-run series benchmarks (010 research R12, quickstart §3).

Everything runs through the real app and the provider the settings select (Ollama
`llama3.1:8b` by default), so only modules marked `benchmark` use these steps.
"""

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from fastapi.testclient import TestClient

from app.podcasts.catalog import SHOW_TEMPLATES
from tests.support.podcast_harness import CATALOG, EPISODES, lines_of, parse_sse

SERIES = "/api/podcasts/series"
REVIEW_SHEET = (
    Path(__file__).resolve().parents[4]
    / "specs"
    / "010-recurring-podcast-shows"
    / "series-review-sheet.md"
)
NEUTRAL_REPLIES = (
    "¡Qué interesante! Cuéntame más.",
    "No lo sabía. ¿Y por qué pasa eso?",
    "Me parece una buena idea.",
    "Sí, estoy de acuerdo contigo.",
)
MAX_STEPS = 60


@dataclass
class PlayedEpisode:
    conversation_id: int
    host_lines: list[str] = field(default_factory=list)
    first_line_seconds: float | None = None


def show_ids() -> list[str]:
    return list(SHOW_TEMPLATES)


def listing(client: TestClient, show_id: str) -> dict:
    return next(show for show in client.get(CATALOG).json()["shows"] if show["show_id"] == show_id)


def start_series(client: TestClient, show_id: str, format: str, length: str = "short") -> dict:
    body = {"show": listing(client, show_id), "format": format, "length": length}
    response = client.post(EPISODES, json={**body, "kind": "series", "learner_name": "Sam"})
    assert response.status_code == 201, response.text
    return response.json()


def start_one_off(client: TestClient, show_id: str, format: str) -> dict:
    body = {"show": listing(client, show_id), "format": format, "length": "short"}
    response = client.post(EPISODES, json={**body, "kind": "one_off", "learner_name": "Sam"})
    assert response.status_code == 201, response.text
    return response.json()


def warm(client: TestClient, conversation_id: int) -> None:
    """Warm the episode's session as the episode screen does on load, before its first line."""
    response = client.post(f"{EPISODES}/{conversation_id}/session")
    assert response.status_code == 202, response.text


def post_action(client: TestClient, conversation_id: int, action: str, body=None) -> list[dict]:
    with client.stream("POST", f"{EPISODES}/{conversation_id}/{action}", json=body) as response:
        response.read()
        return parse_sse(response.text)


def say(client: TestClient, conversation_id: int, text: str) -> list[dict]:
    body = {"content": text, "input_source": "keyboard"}
    return post_action(client, conversation_id, "message", body)


def play(
    client: TestClient, conversation_id: int, replies: list[str], max_host_lines: int
) -> PlayedEpisode:
    """Continue and reply in turn until `max_host_lines` host lines, or the episode ends."""
    played = PlayedEpisode(conversation_id)
    queue = list(replies)
    for _step in range(MAX_STEPS):
        state = client.get(f"{EPISODES}/{conversation_id}").json()
        if state["turn"] == "finished" or len(played.host_lines) >= max_host_lines:
            break
        _advance(client, state, queue, played)
    return played


def _advance(client: TestClient, state: dict, queue: list[str], played: PlayedEpisode) -> None:
    started = time.perf_counter()
    if state["turn"] == "learner":
        reply = queue.pop(0) if queue else NEUTRAL_REPLIES[len(played.host_lines) % 4]
        frames = say(client, played.conversation_id, reply)
    else:
        frames = post_action(client, played.conversation_id, "next")
    lines = [line["content"] for line in lines_of(frames)]
    if lines and played.first_line_seconds is None:
        played.first_line_seconds = time.perf_counter() - started
    played.host_lines.extend(lines)


def end(client: TestClient, conversation_id: int) -> None:
    post_action(client, conversation_id, "end")


def wait_for_memory(client: TestClient, series_id: int) -> tuple[dict, float]:
    started = time.perf_counter()
    outcome = client.post(f"{SERIES}/{series_id}/memory?wait=true").json()
    return outcome, time.perf_counter() - started


def remembered(client: TestClient, series_id: int) -> dict:
    return client.get(f"{SERIES}/{series_id}").json()["remembered"]


def write_sheet(title: str, lines: list[str]) -> None:
    """Write one `## title` section of the review sheet, replacing it if present."""
    text = REVIEW_SHEET.read_text(encoding="utf-8") if REVIEW_SHEET.exists() else SHEET_INTRO
    intro, *sections = re.split(r"(?m)^## ", text)
    kept = [section for section in sections if not section.startswith(title)]
    kept.append("\n".join([title, "", *lines]))
    body = "\n\n".join(f"## {section.rstrip()}" for section in kept)
    REVIEW_SHEET.write_text(f"{intro.rstrip()}\n\n{body}\n", encoding="utf-8")


SHEET_INTRO = """# Series review sheet (010)

Written by the hand-run benchmarks (quickstart §3). The review columns are filled by hand.
"""
