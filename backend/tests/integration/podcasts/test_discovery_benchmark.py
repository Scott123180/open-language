"""SC-007: Find a new show gives three suitable, new suggestions within 30 s (research R12).

Hand-run against the real default model, deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k discovery

Ten requests, half with saved interests. Each prints its time, its titles and any duplicate of
a ready-made title; the reviewer judges suitability from the printed titles and premises.
"""

import time

import pytest

from app.podcasts.catalog import MIN_SUGGESTIONS, SHOW_TEMPLATES
from app.podcasts.services.discovery import normalise_title
from tests.integration.podcasts.podcast_harness import real_podcast_app
from tests.integration.podcasts.series_benchmark import write_sheet

pytestmark = pytest.mark.benchmark

REQUESTS = 10
SC_007_SECONDS = 30.0
INTERESTS = ["chess", "jazz", "cycling"]
NOT_ENOUGH_STATUS = 503


def _request(client, index: int) -> tuple[float, int, dict]:
    client.put("/api/podcasts/preferences", json={"interests": INTERESTS if index % 2 else []})
    started = time.perf_counter()
    response = client.post("/api/podcasts/shows/discover", json={"avoid_titles": []})
    return time.perf_counter() - started, response.status_code, response.json()


def _row(index: int, seconds: float, status: int, body: dict) -> str:
    ready_made = {normalise_title(template.title) for template in SHOW_TEMPLATES.values()}
    shows = body.get("suggestions", [])
    duplicates = [s["title"] for s in shows if normalise_title(s["title"]) in ready_made]
    listed = "; ".join(f"{s['title']} — {s['premise']}" for s in shows) or body.get("detail", "")
    return f"| {index + 1} | {seconds:.1f} s | {status} | {len(shows)} | {', '.join(duplicates) or '—'} | {listed} |  |"


def test_ten_requests_give_three_new_suggestions_in_time(tmp_path):
    with real_podcast_app(tmp_path, "es") as harness:
        results = [_request(harness.client, index) for index in range(REQUESTS)]
    rows = [_row(index, *result) for index, result in enumerate(results)]
    table = [
        "| Request | Time | Status | Count | Ready-made duplicates | Suggestions | Suitable (Y/N) |",
        "|---|---|---|---|---|---|---|",
        *rows,
    ]
    write_sheet(
        "SC-007: Find a new show",
        ["Odd requests carry saved interests (chess, jazz, cycling).", "", *table],
    )
    for row in rows:
        print(row)  # noqa: T201
    assert all(seconds <= SC_007_SECONDS for seconds, _status, _body in results)
    assert all(
        status == NOT_ENOUGH_STATUS or len(body["suggestions"]) >= MIN_SUGGESTIONS
        for _s, status, body in results
    )
