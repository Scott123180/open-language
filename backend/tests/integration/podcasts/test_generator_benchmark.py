"""SC-007 and SC-008: generated shows are on the idea and playable; Surprise me varies.

Hand-run against the real default model, deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k generator

SC-007 asks a human whether each show is on its idea, so every idea is printed beside the
title, premise and topic. The code checks what it can: at least 18 of 20 ideas give a show
that plays end to end with two different hosts whose names come from the language's name bank.
"""

import pytest

from app.practice_languages import host_names_for
from app.services.tts.voices import AVAILABLE_VOICES
from tests.integration.podcasts.podcast_harness import RealPodcastHarness, real_podcast_app

pytestmark = pytest.mark.benchmark

IDEAS = (
    "football tactics",
    "living abroad as a nurse",
    "the best street food in Mexico City",
    "learning to surf at forty",
    "running a small bakery",
    "why cats knock things off tables",
    "commuting by bicycle in winter",
    "a first trip to Japan",
    "growing tomatoes on a balcony",
    "starting a book club",
    "retro video games",
    "planning a wedding on a budget",
    "the life of a lighthouse keeper",
    "moving back in with your parents",
    "learning the guitar",
    "night markets",
    "training for a marathon",
    "the history of chocolate",
    "working in a hotel kitchen",
    "adopting a rescue dog",
)
PLAYABLE_BAR = 18
SURPRISE_PRESSES = 20
DISTINCT_SURPRISE_BAR = 15
LEARNER_TURNS = 2
GENDER = {voice.key: voice.gender for voice in AVAILABLE_VOICES}


def _is_playable(harness: RealPodcastHarness, draft: dict, language: str) -> bool:
    lead, second = draft["hosts"]
    if lead["name"] == second["name"]:
        return False
    if any(
        host["name"] not in host_names_for(language, GENDER[host["voice_key"]])
        for host in (lead, second)
    ):
        return False
    run = harness.play(harness.start_draft(draft, "panel"), LEARNER_TURNS)
    return len(run.host_lines) > 0


def _generate(harness: RealPodcastHarness, idea: str) -> dict | None:
    response = harness.client.post("/api/podcasts/shows/generate", json={"idea": idea})
    return response.json() if response.status_code == 200 else None


def test_generated_shows_are_playable_with_suitable_hosts(tmp_path):
    with real_podcast_app(tmp_path, "es") as harness:
        drafts = {idea: _generate(harness, idea) for idea in IDEAS}
        playable = [
            idea for idea, draft in drafts.items() if draft and _is_playable(harness, draft, "es")
        ]
    summary = f"{len(playable)}/{len(IDEAS)} playable; check each is on its idea:"
    print(f"\nSC-007: {summary}")  # noqa: T201
    for idea, draft in drafts.items():
        shown = f"{draft['title']} — {draft['premise']} ({draft['topic']})" if draft else "declined"
        print(f"  {idea!r}: {shown}")  # noqa: T201
    assert len(playable) >= PLAYABLE_BAR


def test_twenty_surprise_presses_vary(tmp_path):
    with real_podcast_app(tmp_path, "es") as harness:
        drafts = [
            harness.client.post("/api/podcasts/shows/surprise", json={}).json()
            for _ in range(SURPRISE_PRESSES)
        ]
    topics = {draft["topic"].casefold() for draft in drafts}
    titles = {draft["title"].casefold() for draft in drafts}
    counts = f"{len(topics)} topics, {len(titles)} titles"
    print(f"\nSC-008: {counts} in {SURPRISE_PRESSES} presses")  # noqa: T201
    assert len(topics) >= DISTINCT_SURPRISE_BAR
    assert len(titles) == SURPRISE_PRESSES
