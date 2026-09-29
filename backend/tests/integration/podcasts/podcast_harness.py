"""Hand-run harness for the podcast benchmarks: the real app, the real provider, real voices.

Nothing here is faked except the database, which is a scratch file. The provider is the one the
settings select (Ollama `llama3.1:8b` by default), so every benchmark that uses this harness is
marked `benchmark` and deselected from the default run (quickstart §3).
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.podcasts.catalog import SHOW_TEMPLATES
from tests.support.podcast_harness import EPISODES, parse_sse, serve_sessions
from tests.support.scratch_database import make_sessions

LEARNER_REPLIES = {
    "es": (
        "Me gusta mucho cocinar los fines de semana.",
        "No estoy de acuerdo, creo que es muy caro.",
        "¿Y tú qué piensas?",
        "Ayer fui al mercado con mi hermana.",
        "Es interesante, no lo sabía.",
    ),
    "de": (
        "Ich koche am Wochenende sehr gern.",
        "Das finde ich nicht, es ist zu teuer.",
        "Und was denkst du?",
        "Gestern war ich mit meiner Schwester auf dem Markt.",
        "Das ist interessant, das wusste ich nicht.",
    ),
}
MAX_STEPS = 80


@dataclass
class RunResult:
    """One benchmark episode: its stored lines and how long each line took to arrive."""

    conversation_id: int
    lines: list[dict]
    hosts: list[dict]
    line_seconds: list[float] = field(default_factory=list)

    @property
    def host_lines(self) -> list[dict]:
        return [line for line in self.lines if line["speaker"] == "host"]


@dataclass
class RealPodcastHarness:
    client: TestClient

    def run_episode(
        self, format: str, show_index: int, learner_turns: int, length: str = "short"
    ) -> RunResult:
        episode_id = self._start(format, show_index, length)
        timings: list[float] = []
        replies = iter(LEARNER_REPLIES[self.language] * learner_turns)
        for _step in range(MAX_STEPS):
            state = self.client.get(f"{EPISODES}/{episode_id}").json()
            if state["turn"] == "finished":
                break
            timings.append(self._advance(episode_id, state, replies, learner_turns))
            learner_turns -= state["turn"] == "learner"
        episode = self.client.get(f"{EPISODES}/{episode_id}").json()
        return RunResult(episode_id, episode["lines"], episode["hosts"], timings)

    @property
    def language(self) -> str:
        return self.client.get("/api/settings").json()["target_language"]

    def _start(self, format: str, show_index: int, length: str) -> int:
        show_id = list(SHOW_TEMPLATES)[show_index % len(SHOW_TEMPLATES)]
        shows = self.client.get("/api/podcasts/catalog").json()["shows"]
        draft = next(show for show in shows if show["show_id"] == show_id)
        body = {"show": draft, "format": format, "length": length}
        return self.client.post(EPISODES, json=body).json()["conversation_id"]

    def _advance(self, episode_id: int, state: dict, replies: Iterator[str], left: int) -> float:
        started = time.perf_counter()
        if state["turn"] == "learner" and left <= 0:
            self._post(episode_id, "end")
        elif state["turn"] == "learner":
            self._post(
                episode_id, "message", {"content": next(replies), "input_source": "keyboard"}
            )
        else:
            self._post(episode_id, "next")
        return time.perf_counter() - started

    def _post(self, episode_id: int, action: str, body: dict | None = None) -> list[dict]:
        with self.client.stream("POST", f"{EPISODES}/{episode_id}/{action}", json=body) as response:
            response.read()
            return parse_sse(response.text)

    def roleplay_replies(self, scenario_id: str, learner_turns: int) -> list[str]:
        """Roleplay partner replies to the same learner lines, for SC-006's comparison."""
        conversation = self.client.post(
            "/api/conversations", json={"scenario_id": scenario_id}
        ).json()
        self._chat(f"/api/chat/{conversation['id']}/open", None)
        replies = LEARNER_REPLIES[self.language][:learner_turns]
        for reply in replies:
            self._chat(f"/api/chat/{conversation['id']}/message", {"content": reply})
        messages = self.client.get(f"/api/conversations/{conversation['id']}/messages").json()
        return [message["content"] for message in messages if message["role"] == "assistant"]

    def _chat(self, path: str, body: dict | None) -> None:
        with self.client.stream("POST", path, json=body) as response:
            response.read()


@contextmanager
def real_podcast_app(
    tmp_path: Path, language: str, level: str = "natural"
) -> Iterator[RealPodcastHarness]:
    sessions = make_sessions(tmp_path / "benchmark.db")
    opened: list[Session] = []
    serve_sessions(sessions, opened)
    try:
        with TestClient(app) as client:
            client.put(
                "/api/settings", json={"target_language": language, "conversation_level": level}
            )
            yield RealPodcastHarness(client)
    finally:
        app.dependency_overrides.clear()
        for session in opened:
            session.close()
