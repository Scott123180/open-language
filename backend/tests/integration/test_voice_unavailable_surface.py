"""T019: a missing voice reaches the learner as a plain 503, never a 500 (research R6)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.services.tts.base import VoiceUnavailable

PROBE_PATH = "/__probe/voice-unavailable"
MESSAGE = "The German voice isn't installed. Run ./run.sh --setup to download it."


def _raise_voice_unavailable():
    raise VoiceUnavailable(MESSAGE)


@pytest.fixture()
def client():
    fastapi_app.add_api_route(PROBE_PATH, _raise_voice_unavailable, methods=["GET"])
    probe = fastapi_app.router.routes[-1]
    with TestClient(fastapi_app, raise_server_exceptions=False) as test_client:
        yield test_client
    fastapi_app.router.routes.remove(probe)


def test_voice_unavailable_is_503_with_its_message(client):
    response = client.get(PROBE_PATH)

    assert (response.status_code, response.json()) == (503, {"detail": MESSAGE})
