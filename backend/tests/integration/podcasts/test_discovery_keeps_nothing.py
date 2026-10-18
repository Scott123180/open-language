"""010 T123: Find a new show stores nothing; a suggestion is kept only when favourited or played."""

import sqlite3

import pytest

from app.main import app
from app.services.factory import get_structured_llm
from tests.support.podcast_harness import CATALOG, EPISODES, podcast_harness
from tests.support.scripted_memory_llm import ScriptedMemoryLLM
from tests.support.scripted_show_llm import SUITABLE_SHOW

DISCOVER = "/api/podcasts/shows/discover"


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        llm = ScriptedMemoryLLM(
            {"shows": [{**SUITABLE_SHOW, "title": t} for t in ("Uno", "Dos", "Tres")]}
        )
        app.dependency_overrides[get_structured_llm] = lambda: llm
        podcast.db_file = tmp_path / "podcasts.db"
        yield podcast


def _counts(db_file) -> dict[str, int]:
    with sqlite3.connect(db_file) as conn:
        tables = [
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        ]
        return {
            table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in tables
        }


def _suggestions(harness) -> list[dict]:
    return harness.client.post(DISCOVER, json={"avoid_titles": []}).json()["suggestions"]


def test_discovery_writes_no_row_and_leaves_the_ready_made_list(harness):
    shows_before = harness.client.get(CATALOG).json()["shows"]
    before = _counts(harness.db_file)

    _suggestions(harness)

    assert _counts(harness.db_file) == before
    assert harness.client.get(CATALOG).json()["shows"] == shows_before


def test_a_favourited_suggestion_is_kept_in_my_shows(harness):
    suggestion = _suggestions(harness)[0]

    harness.client.put("/api/podcasts/favourites", json={"show": suggestion, "is_favourite": True})

    assert [show["title"] for show in harness.client.get(CATALOG).json()["my_shows"]] == ["Uno"]


def test_a_started_suggestion_is_kept(harness):
    suggestion = _suggestions(harness)[1]

    harness.client.post(
        EPISODES, json={"show": suggestion, "format": "panel", "length": "short", "kind": "series"}
    )

    assert [show["title"] for show in harness.client.get(CATALOG).json()["my_shows"]] == ["Dos"]


def test_ignored_suggestions_leave_nothing_behind(harness):
    _suggestions(harness)
    _suggestions(harness)

    assert harness.client.get(CATALOG).json()["my_shows"] == []
