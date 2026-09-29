"""T116: POST /api/podcasts/hosts/shuffle and GET /api/podcasts/voice-sample (contracts §4, §5)."""

import pytest

from app.practice_languages import voice_sample_line
from app.services.tts.voices import voices_for
from tests.support.podcast_harness import podcast_harness, ready_made_draft

SHUFFLE = "/api/podcasts/hosts/shuffle"
SAMPLE = "/api/podcasts/voice-sample"


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _shuffle_body(client, slot: str = "second", learner_name: str | None = "Sam") -> dict:
    hosts = ready_made_draft(client)["hosts"]
    return {"language": "es", "slot": slot, "hosts": hosts, "learner_name": learner_name}


@pytest.mark.parametrize("slot", ["lead", "second"])
def test_a_shuffle_returns_a_new_host_for_the_slot(harness, slot):
    body = _shuffle_body(harness.client, slot)

    response = harness.client.post(SHUFFLE, json=body)

    new = response.json()
    assert response.status_code == 200
    assert new["slot"] == slot
    assert new["name"] not in [host["name"] for host in body["hosts"]] + ["Sam"]
    assert new["personality_id"] not in [host["personality_id"] for host in body["hosts"]]
    other = next(host for host in body["hosts"] if host["slot"] != slot)
    assert new["voice_key"] != other["voice_key"]


def test_three_shuffles_in_a_row_never_clash(harness):
    body = _shuffle_body(harness.client)
    for slot in ("second", "lead", "second"):
        new = harness.client.post(SHUFFLE, json={**body, "slot": slot}).json()
        body["hosts"] = [new if host["slot"] == slot else host for host in body["hosts"]]
        lead, second = body["hosts"]
        assert lead["name"] != second["name"]
        assert lead["personality_id"] != second["personality_id"]
        assert lead["voice_key"] != second["voice_key"]


def test_a_shuffle_with_an_unknown_personality_is_refused(harness):
    body = _shuffle_body(harness.client)
    body["hosts"][0]["personality_id"] = "astronaut"

    assert harness.client.post(SHUFFLE, json=body).status_code == 422


def test_a_shuffle_in_another_language_is_refused(harness):
    body = {**_shuffle_body(harness.client), "language": "de"}

    response = harness.client.post(SHUFFLE, json=body)

    assert response.status_code == 422
    assert "Pick the show again" in response.json()["detail"]


def test_a_voice_sample_is_the_languages_sample_line_in_that_voice(harness):
    voice = voices_for("es")[0].key

    response = harness.client.get(SAMPLE, params={"voice_key": voice, "name": "Lucía"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert harness.speech.synthesized[-1][:2] == (voice, voice_sample_line("es", "Lucía"))


def test_a_second_sample_for_the_same_voice_and_name_is_not_synthesised_again(harness):
    params = {"voice_key": voices_for("es")[0].key, "name": "Lucía"}

    first = harness.client.get(SAMPLE, params=params)
    second = harness.client.get(SAMPLE, params=params)

    assert len(harness.speech.synthesized) == 1
    assert first.content == second.content


def test_a_different_name_is_synthesised_separately(harness):
    voice = voices_for("es")[0].key

    harness.client.get(SAMPLE, params={"voice_key": voice, "name": "Lucía"})
    harness.client.get(SAMPLE, params={"voice_key": voice, "name": "Marco"})

    assert len(harness.speech.synthesized) == 2


def test_an_uninstalled_voice_is_a_503(tmp_path):
    installed, missing = (voice.key for voice in voices_for("es"))
    with podcast_harness(tmp_path, installed={installed}) as harness:
        response = harness.client.get(SAMPLE, params={"voice_key": missing, "name": "Marco"})

    assert response.status_code == 503
    assert "Marco" in response.json()["detail"]


def test_an_unknown_voice_is_a_422(harness):
    response = harness.client.get(SAMPLE, params={"voice_key": "xx_XX-nobody-low", "name": "Ana"})

    assert response.status_code == 422


def test_a_name_over_the_limit_is_a_422(harness):
    params = {"voice_key": voices_for("es")[0].key, "name": "x" * 41}

    assert harness.client.get(SAMPLE, params=params).status_code == 422
