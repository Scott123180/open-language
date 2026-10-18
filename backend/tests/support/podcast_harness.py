"""The podcast harness: the real app over a scratch database, a scripted line writer, fake voices.

Every request gets its own database session, as `get_db` gives it in production, because host
lines are spoken on a worker thread. Settings are read from storage, so a PUT to settings reaches
the next line. The turn policy draws from a seeded random source, so every run takes the same
turns. Series memory (010) is always kept by a scripted structured provider, on the harness's
own database, with catch-ups run at once on the request's thread.
"""

import json
import random
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from app.podcasts.services.series_memory import MemoryCatchUps, SeriesMemoryKeeper
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.database import get_db
from app.main import app
from app.podcasts.services.sqlite_series_storage import SQLiteSeriesStorage
from app.podcasts.services.sqlite_storage import SQLitePodcastStorage
from app.services.conversation import ConversationEngine
from app.services.factory import (
    get_memory_catch_ups,
    get_memory_sessions,
    get_series_memory_keeper,
    memory_stores,
)
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.support.engine_overrides import install_session_provider
from tests.support.fake_speech import RecordingTtsBuilder, override_speech
from tests.support.scratch_database import make_sessions
from tests.support.scripted_line_writer import ScriptedLineWriter
from tests.support.scripted_memory_llm import ScriptedMemoryLLM
from tests.support.synchronous_executor import SynchronousExecutor

POLICY_SEED = 7
READY_MADE_SHOW = "weekend-food-talk"
SERIES_SHOW = "big-little-questions"
EPISODES = "/api/podcasts/episodes"
CATALOG = "/api/podcasts/catalog"


@dataclass
class PodcastHarness:
    client: TestClient
    writer: ScriptedLineWriter
    engine: ConversationEngine
    speech: RecordingTtsBuilder
    sessions: sessionmaker
    memory: ScriptedMemoryLLM
    catch_ups: MemoryCatchUps

    def session(self) -> Session:
        """A fresh session for the test's own reads, never shared with a request."""
        return self.sessions()

    @property
    def podcasts(self) -> SQLitePodcastStorage:
        return SQLitePodcastStorage(self.session())

    @property
    def conversations(self) -> SQLiteStorageProvider:
        return SQLiteStorageProvider(self.session())

    def start(self, format: str, length: str = "short", learner_name: str | None = None) -> int:
        return start_episode(self.client, format, length, learner_name)["conversation_id"]

    def stream(self, conversation_id: int, action: str, **body) -> list[dict]:
        """POST an SSE action and return its frames."""
        return post_stream(self.client, f"{EPISODES}/{conversation_id}/{action}", body or None)

    def say(self, conversation_id: int, content: str, **body) -> list[dict]:
        payload = {"content": content, "input_source": "keyboard", **body}
        return self.stream(conversation_id, "message", **payload)

    def episode(self, conversation_id: int) -> dict:
        return self.client.get(f"{EPISODES}/{conversation_id}").json()

    @property
    def series_storage(self) -> SQLiteSeriesStorage:
        return SQLiteSeriesStorage(self.session())

    def listing(self, show_id: str = SERIES_SHOW) -> dict:
        """The show as the catalogue lists it now: with its series' hosts once it has one."""
        return next(s for s in self.client.get(CATALOG).json()["shows"] if s["show_id"] == show_id)

    def start_series(self, format: str = "one_host", show_id: str = SERIES_SHOW, **body) -> dict:
        """Start the next series episode of the listed show; return the new episode."""
        payload = {"show": self.listing(show_id), "format": format, "length": "short", **body}
        response = self.client.post(EPISODES, json={**payload, "kind": "series"})
        assert response.status_code == 201, response.text
        return response.json()

    def play_through(self, conversation_id: int) -> None:
        """Ask for host lines, replying when invited, until the episode has signed off."""
        for _step in range(60):
            state = self.episode(conversation_id)
            if state["turn"] == "finished":
                return
            if state["turn"] == "learner":
                self.say(conversation_id, "Me encanta este tema.")
            else:
                self.stream(conversation_id, "next")
        raise AssertionError("the episode never finished")


def install_seeded_policy(seed: int = POLICY_SEED) -> None:
    from app.podcasts.routes import get_turn_policy
    from app.podcasts.services.turn_policy import TurnPolicy

    app.dependency_overrides[get_turn_policy] = lambda: TurnPolicy(random.Random(seed))


def install_sample_cache(directory: Path) -> None:
    from app.podcasts.host_routes import get_sample_cache_dir

    app.dependency_overrides[get_sample_cache_dir] = lambda: directory


def serve_sessions(sessions: sessionmaker, opened: list[Session]) -> None:
    """One session per request, closed only when the harness closes.

    A host line is spoken on a worker thread that records the audio path with the request's
    session after the response has gone, so closing it at the end of the request would race.
    """

    def scratch_db() -> Session:
        opened.append(sessions())
        return opened[-1]

    app.dependency_overrides[get_db] = scratch_db


def install_series_memory(sessions: sessionmaker) -> tuple[ScriptedMemoryLLM, MemoryCatchUps]:
    """Keep series memory with a scripted provider on the harness database, synchronously."""
    memory = ScriptedMemoryLLM()
    catch_ups = MemoryCatchUps(SynchronousExecutor())
    app.dependency_overrides[get_memory_sessions] = lambda: sessions
    app.dependency_overrides[get_memory_catch_ups] = lambda: catch_ups
    app.dependency_overrides[get_series_memory_keeper] = lambda: SeriesMemoryKeeper(
        memory, memory_stores(sessions)
    )
    return memory, catch_ups


@contextmanager
def podcast_harness(tmp_path: Path, installed: set[str] | None = None) -> Iterator[PodcastHarness]:
    """The harness on a new database. `installed` limits the installed voices (None: all)."""
    sessions = make_sessions(tmp_path / "podcasts.db")
    with podcast_harness_on(sessions, tmp_path, installed) as harness:
        yield harness


@contextmanager
def podcast_harness_on(
    sessions: sessionmaker, tmp_path: Path, installed: set[str] | None = None
) -> Iterator[PodcastHarness]:
    """The harness on an existing database, such as an upgraded one."""
    opened: list[Session] = []
    serve_sessions(sessions, opened)
    writer = ScriptedLineWriter()
    engine = install_session_provider(app, writer)
    speech = override_speech(app, installed=installed)
    install_seeded_policy()
    install_sample_cache(tmp_path / "voice_samples")
    memory, catch_ups = install_series_memory(sessions)
    try:
        with TestClient(app) as client:
            yield PodcastHarness(client, writer, engine, speech, sessions, memory, catch_ups)
    finally:
        app.dependency_overrides.clear()
        for session in opened:
            session.close()


def parse_sse(raw_text: str) -> list[dict]:
    return [
        json.loads(line[len("data: ") :])
        for line in raw_text.splitlines()
        if line.startswith("data: ")
    ]


def post_stream(client: TestClient, path: str, body: dict | None = None) -> list[dict]:
    with client.stream("POST", path, json=body) as response:
        response.read()
        assert response.status_code == 200, response.text
        return parse_sse(response.text)


def ready_made_draft(client: TestClient, show_id: str = READY_MADE_SHOW) -> dict:
    shows = client.get("/api/podcasts/catalog").json()["shows"]
    return next(show for show in shows if show["show_id"] == show_id)


def start_episode(
    client: TestClient, format: str, length: str = "short", learner_name: str | None = None
) -> dict:
    """Start the ready-made show in `format` and return the new episode."""
    body = {"show": ready_made_draft(client), "format": format, "length": length}
    if learner_name is not None:
        body["learner_name"] = learner_name
    response = client.post(EPISODES, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def lines_of(frames: list[dict]) -> list[dict]:
    return [frame["line"] for frame in frames if frame.get("event") == "line"]


def done_of(frames: list[dict]) -> dict:
    return next(frame for frame in frames if frame.get("done"))
