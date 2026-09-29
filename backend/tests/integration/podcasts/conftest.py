"""The podcast harness: the real app over a scratch database, a scripted line writer, fake voices.

Every request gets its own database session, as `get_db` gives it in production, because host
lines are spoken on a worker thread. Settings are read from storage, so a PUT to settings reaches
the next line. The turn policy draws from a seeded random source, so every run takes the same
turns.
"""

import random
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.database import get_db
from app.main import app
from app.services.conversation import ConversationEngine
from tests.support.engine_overrides import install_session_provider
from tests.support.fake_speech import RecordingTtsBuilder, override_speech
from tests.support.scratch_database import make_sessions
from tests.support.scripted_line_writer import ScriptedLineWriter

POLICY_SEED = 7
READY_MADE_SHOW = "weekend-food-talk"


@dataclass
class PodcastHarness:
    client: TestClient
    writer: ScriptedLineWriter
    engine: ConversationEngine
    speech: RecordingTtsBuilder
    sessions: sessionmaker

    def session(self) -> Session:
        """A fresh session for the test's own reads, never shared with a request."""
        return self.sessions()


def install_seeded_policy(seed: int = POLICY_SEED) -> None:
    from app.podcasts.router import get_turn_policy
    from app.podcasts.services.turn_policy import TurnPolicy

    app.dependency_overrides[get_turn_policy] = lambda: TurnPolicy(random.Random(seed))


def serve_sessions(sessions: sessionmaker) -> None:
    def scratch_db() -> Iterator[Session]:
        db = sessions()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = scratch_db


@pytest.fixture
def podcast_client(tmp_path: Path):
    sessions = make_sessions(tmp_path / "podcasts.db")
    serve_sessions(sessions)
    writer = ScriptedLineWriter()
    engine = install_session_provider(app, writer)
    speech = override_speech(app)
    install_seeded_policy()
    with TestClient(app) as client:
        yield PodcastHarness(client, writer, engine, speech, sessions)
    app.dependency_overrides.clear()


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
    response = client.post("/api/podcasts/episodes", json=body)
    assert response.status_code == 201, response.text
    return response.json()
