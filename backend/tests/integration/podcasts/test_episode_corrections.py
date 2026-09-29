"""T046: corrections behave in an episode exactly as in a roleplay (FR-027)."""

from fastapi import Depends

from app.corrections.services.evaluator import CorrectionEvaluator, CorrectionFinding
from app.corrections.services.pause_tracker import CorrectionPauseTracker
from app.corrections.services.strategies import GentleCorrectionStrategy, StrictCorrectionStrategy
from app.main import app
from app.services.factory import get_correction_storage, get_correction_strategy
from tests.support.podcast_harness import done_of, lines_of

FINDING = CorrectionFinding(
    category="conjugation",
    error_fragment="Yo tener",
    corrected_text="Yo tengo veinte años",
    explanation="Tener must be conjugated as tengo with yo.",
    rank=0,
)


class ScriptedEvaluator(CorrectionEvaluator):
    def __init__(self, findings) -> None:
        self.findings = findings

    def evaluate(self, request):
        return self.findings


def _use_gentle(findings=(FINDING,)) -> None:
    strategy = GentleCorrectionStrategy(ScriptedEvaluator(findings))
    app.dependency_overrides[get_correction_strategy] = lambda: strategy


def _use_strict(findings=(FINDING,)) -> None:
    evaluator = ScriptedEvaluator(findings)

    def strict(correction_storage=Depends(get_correction_storage)):
        return StrictCorrectionStrategy(evaluator, CorrectionPauseTracker(correction_storage))

    app.dependency_overrides[get_correction_strategy] = strict


def _kinds(frames: list[dict]) -> list[str]:
    return ["done" if f.get("done") else f.get("event", "error") for f in frames]


def _learners_turn(podcast_client) -> int:
    episode_id = podcast_client.start("one_host")
    podcast_client.stream(episode_id, "next")
    return episode_id


def test_gentle_replies_with_the_recast_and_streams_no_note(podcast_client):
    _use_gentle()
    episode_id = _learners_turn(podcast_client)

    frames = podcast_client.say(episode_id, "Yo tener veinte años")

    assert _kinds(frames) == ["user_message_saved", "line", "done"]
    assert podcast_client.writer.guidance[-1]
    assert done_of(frames)["turn"] == "learner"


def test_strict_pauses_the_learners_message_with_no_host_line(podcast_client):
    _use_strict()
    episode_id = _learners_turn(podcast_client)

    frames = podcast_client.say(episode_id, "Yo tener veinte años")

    assert _kinds(frames) == ["user_message_saved", "feedback", "done"]
    assert lines_of(frames) == []
    assert (done_of(frames)["turn"], done_of(frames)["awaiting"]) == ("learner", None)


def test_a_paused_episode_still_reads_as_the_learners_turn(podcast_client):
    _use_strict()
    episode_id = _learners_turn(podcast_client)
    podcast_client.say(episode_id, "Yo tener veinte años")

    episode = podcast_client.episode(episode_id)

    assert (episode["turn"], episode["awaiting"]) == ("learner", None)


def test_the_retry_after_a_pause_gets_the_hosts_reply(podcast_client):
    _use_strict()
    episode_id = _learners_turn(podcast_client)
    podcast_client.say(episode_id, "Yo tener veinte años")
    _use_strict(findings=())

    frames = podcast_client.say(episode_id, "Yo tengo veinte años")

    assert _kinds(frames) == ["user_message_saved", "line", "done"]


def test_a_low_confidence_spoken_message_is_gated_as_in_chat(podcast_client):
    _use_strict()
    episode_id = _learners_turn(podcast_client)

    frames = podcast_client.say(
        episode_id, "Yo tener veinte años", input_source="voice", transcription_confidence=0.2
    )

    feedback = next(frame for frame in frames if frame.get("event") == "feedback")
    assert [note["kind"] for note in feedback["notes"]] == ["repeat_request"]
