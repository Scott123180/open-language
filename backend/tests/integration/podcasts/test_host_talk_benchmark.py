"""011 T062: configured host talk on the real model (SC-001–SC-003, SC-005, SC-011–SC-015).

Hand-run on the default local setup, deselected by default:

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k host_talk

Medium One host and Medium Panel episodes of Big Little Questions at Beginner, with the default
settings, each played past its wrap-up to its sign-off with scripted learner questions and a
last thought. The figures and the transcripts to review are printed and written to
`OPEN_LANGUAGE_BENCH_REPORT` (default: the system temporary folder) before any assertion runs.
`OPEN_LANGUAGE_BENCH_EPISODES` sets the episodes per format (default 20).
"""

import os
import statistics
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from app.podcasts.services import line_address
from app.podcasts.services.sqlite_storage import SQLitePodcastStorage
from tests.integration.conversation_levels.text_metrics import split_sentences, words
from tests.integration.podcasts.podcast_harness import real_podcast_app
from tests.support.podcast_harness import EPISODES, parse_sse

pytestmark = pytest.mark.benchmark

SHOW_INDEX = 7
"""Big Little Questions in the ready-made catalogue."""
EPISODE_COUNT = int(os.environ.get("OPEN_LANGUAGE_BENCH_EPISODES", "20"))
REPORT = Path(os.environ.get("OPEN_LANGUAGE_BENCH_REPORT", tempfile.gettempdir())) / "host-talk.md"
MAX_STEPS = 70
BEGINNER_WORDS = 8
DISCUSSION = {"react", "explain", "story", "answer", "follow_up"}
QUESTIONS = (
    "¿Por qué bostezamos?",
    "Me gusta mucho dormir la siesta.",
    "¿Cuánto tiempo dura un bostezo?",
    "No lo sabía, es interesante.",
    "¿Los animales también bostezan?",
)
FOR_BOTH = "¿Qué les gusta a ustedes dos?"
LAST_THOUGHT = "Me gustó mucho el programa."


@dataclass
class Tags:
    """Every address read during the run: whether a tag or the fallback decided."""

    from_tag: int = 0
    total: int = 0

    def share(self) -> float:
        return self.from_tag / self.total if self.total else 0.0


@dataclass
class Episode:
    format: str
    lines: list = field(default_factory=list)

    @property
    def host_lines(self) -> list:
        return [line for line in self.lines if line.is_host]


@pytest.fixture
def tags(monkeypatch) -> Tags:
    counted, read = Tags(), line_address.LineAddress.read

    def counting(self, text):
        result = read(self, text)
        counted.total += 1
        counted.from_tag += result.is_from_tag
        return result

    monkeypatch.setattr(line_address.LineAddress, "read", counting)
    return counted


def _post(client, episode_id: int, action: str, body: dict | None = None) -> None:
    with client.stream("POST", f"{EPISODES}/{episode_id}/{action}", json=body) as response:
        response.read()
        parse_sse(response.text)


def _reply(state: dict, replies: list[str]) -> str:
    has_wrapped = any(line["intent"] == "wrap_up" for line in state["lines"])
    return LAST_THOUGHT if has_wrapped or not replies else replies.pop(0)


def _play(harness, format: str) -> Episode:
    episode_id = harness._start(format, SHOW_INDEX, "medium")
    replies = [*QUESTIONS, FOR_BOTH] if format == "panel" else list(QUESTIONS)
    for _step in range(MAX_STEPS):
        state = harness.client.get(f"{EPISODES}/{episode_id}").json()
        if state["turn"] == "finished":
            break
        if state["turn"] == "learner":
            body = {"content": _reply(state, replies), "input_source": "keyboard"}
            _post(harness.client, episode_id, "message", body)
        else:
            _post(harness.client, episode_id, "next")
    storage = SQLitePodcastStorage(harness.sessions())
    return Episode(format, list(storage.get_lines(episode_id)))


def _before_wrap_up(episode: Episode) -> list:
    intents = [line.host.intent for line in episode.host_lines]
    end = intents.index("wrap_up") if "wrap_up" in intents else len(intents)
    return episode.host_lines[:end]


def _figures(episodes: list[Episode], tags: Tags) -> dict[str, float]:
    discussion = [line for e in episodes for line in e.host_lines if line.host.intent in DISCUSSION]
    full = [line for line in discussion if line.host.intent in ("explain", "answer")]
    before = [line for e in episodes for line in _before_wrap_up(e)]
    sentences = [
        s for e in episodes for line in e.host_lines for s in split_sentences(line.content)
    ]
    return {
        "median sentences per discussion line (SC-001)": _median_sentences(discussion),
        "median sentences per explain/answer line (SC-013)": _median_sentences(full),
        "inviting share before the wrap-up (SC-001)": _share(
            [line.host.invites_learner for line in before]
        ),
        "sentences within 8 words (SC-002)": _share(
            [len(words(s)) <= BEGINNER_WORDS for s in sentences]
        ),
        "address tag share (R19)": tags.share(),
        "episodes signed off (SC-015)": _share([_signed_off(e) for e in episodes]),
    }


def _median_sentences(lines: list) -> float:
    return statistics.median(len(split_sentences(line.content)) for line in lines) if lines else 0.0


def _share(flags: list[bool]) -> float:
    return sum(flags) / len(flags) if flags else 0.0


def _signed_off(episode: Episode) -> bool:
    return bool(episode.host_lines) and episode.host_lines[-1].host.intent == "sign_off"


def _longest_quiet_run(episode: Episode) -> int:
    longest = run = 0
    for line in episode.lines:
        run = run + 1 if line.is_host and not line.host.invites_learner else 0
        longest = max(longest, run)
    return longest


def _review(episodes: list[Episode]) -> list[str]:
    """Transcripts to review by hand: questions, openings, wrap-ups and sign-offs."""
    rows = []
    for number, episode in enumerate(episodes, start=1):
        lines = episode.lines
        for previous, line in zip(lines, lines[1:], strict=False):
            if not previous.is_host and "?" in previous.content and line.is_host:
                rows.append(
                    f"- E{number} {episode.format} Q: {previous.content} → [{line.host.intent}] {line.content}"
                )
            if (
                line.is_host
                and line.content.rstrip().endswith("?")
                and line.host.addressee != "learner"
            ):
                rows.append(f"- E{number} {episode.format} ?→{line.host.addressee}: {line.content}")
        for line in episode.host_lines:
            if line.host.intent in ("open", "wrap_up", "sign_off"):
                rows.append(f"- E{number} {episode.format} [{line.host.intent}] {line.content}")
    return rows


def _write_report(episodes: list[Episode], figures: dict[str, float]) -> None:
    intents = Counter(line.host.intent for e in episodes for line in e.host_lines)
    lines = ["# Host talk benchmark", "", *(f"- {k}: {v:.2f}" for k, v in figures.items())]
    lines += ["", f"- intents: {dict(intents)}", "", "## To review", "", *_review(episodes)]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:12]), f"\nReport: {REPORT}")  # noqa: T201


def test_configured_hosts_talk_like_podcast_hosts(tmp_path, tags):
    with real_podcast_app(tmp_path, "es", "beginner") as harness:
        episodes = [_play(harness, f) for f in ("one_host", "panel") for _ in range(EPISODE_COUNT)]
    figures = _figures(episodes, tags)
    _write_report(episodes, figures)

    assert all(_longest_quiet_run(episode) <= 4 for episode in episodes)
    assert figures["episodes signed off (SC-015)"] == 1.0
    assert figures["median sentences per discussion line (SC-001)"] >= 3
    assert figures["inviting share before the wrap-up (SC-001)"] <= 0.5
    assert figures["median sentences per explain/answer line (SC-013)"] >= 4
    assert figures["sentences within 8 words (SC-002)"] >= 0.9
