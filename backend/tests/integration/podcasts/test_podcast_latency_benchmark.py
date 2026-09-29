"""SC-009: after Continue, the next host line starts playing within 5 s in 90% of cases.

Hand-run on the default local setup (Ollama and the Piper voices), deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k latency

"Starts playing" is measured to the moment its audio is ready: `GET /api/audio/tts/{id}` returns
the WAV. The time to the `line` frame and the synthesis share are printed separately, so a miss
can be put down to the model or to speech. One Long episode's prompt size is also recorded
(research R14), by asking Ollama once for the prompt the episode's next line would send.
"""

import statistics
import time

import pytest

from app.config import get_settings
from app.conversation_levels import ConversationLevel
from app.podcasts.services.cues import next_turn_history
from app.podcasts.services.episodes import load_episode
from app.podcasts.services.sqlite_storage import SQLitePodcastStorage
from app.podcasts.services.turn_policy import LineCue
from tests.integration.podcasts.podcast_harness import real_podcast_app
from tests.support.podcast_harness import EPISODES, lines_of, parse_sse

pytestmark = pytest.mark.benchmark

PRESSES = 50
SC_009_P90_SECONDS = 5.0
PERCENTILE_90 = 9


def _press_and_wait_for_audio(client, episode_id: int) -> tuple[float, float, bool]:
    """(seconds to the line frame, seconds to its audio, whether the episode finished)."""
    started = time.perf_counter()
    with client.stream("POST", f"{EPISODES}/{episode_id}/next") as response:
        response.read()
        frames = parse_sse(response.text)
    text_ready = time.perf_counter()
    [line] = lines_of(frames)
    assert client.get(f"/api/audio/tts/{line['message_id']}").status_code == 200
    is_finished = any(frame.get("turn") == "finished" for frame in frames)
    return text_ready - started, time.perf_counter() - started, is_finished


def _timed_presses(harness) -> tuple[list[tuple[float, float]], int]:
    """PRESSES Continues over as many Long Listen episodes as it takes; the first episode's id."""
    first = episode_id = _start_long_listen(harness)
    timings = []
    while len(timings) < PRESSES:
        to_text, to_audio, is_finished = _press_and_wait_for_audio(harness.client, episode_id)
        timings.append((to_text, to_audio))
        if is_finished:
            episode_id = _start_long_listen(harness)
    return timings, first


def test_the_next_line_is_ready_to_play_within_five_seconds(tmp_path):
    with real_podcast_app(tmp_path, "es") as harness:
        timings, first_episode = _timed_presses(harness)
        prompt_tokens = _prompt_eval_count(harness, first_episode)
    to_text = [text for text, _audio in timings]
    to_audio = [audio for _text, audio in timings]
    p90 = statistics.quantiles(to_audio, n=10)[PERCENTILE_90 - 1]
    print(  # noqa: T201
        f"\nSC-009 p90 to audio {p90:.2f}s; p90 to text "
        f"{statistics.quantiles(to_text, n=10)[PERCENTILE_90 - 1]:.2f}s; "
        f"mean synthesis {statistics.fmean(a - t for t, a in timings):.2f}s; "
        f"R14 prompt_eval_count at the end of a Long episode: {prompt_tokens}"
    )
    assert p90 <= SC_009_P90_SECONDS


def _start_long_listen(harness) -> int:
    draft = harness.client.get("/api/podcasts/catalog").json()["shows"][0]
    body = {"show": draft, "format": "listen", "length": "long"}
    return harness.client.post(EPISODES, json=body).json()["conversation_id"]


def _prompt_eval_count(harness, episode_id: int) -> int:
    """The tokens Ollama reads for the next line of this episode (research R14)."""
    import ollama

    episode = load_episode(SQLitePodcastStorage(harness.sessions()), episode_id)
    cue = LineCue("lead", "discuss", False, False, False)
    turns = next_turn_history(episode.facts, episode.cast, episode.learner_label, cue)
    system = {"role": "system", "content": episode.standing_prompt(ConversationLevel.NATURAL)}
    messages = [system, *({"role": t.role, "content": t.content} for t in turns)]
    settings = get_settings()
    reply = ollama.Client(host=settings.ollama_url).chat(
        model=settings.ollama_model, messages=messages
    )
    return reply["prompt_eval_count"]
