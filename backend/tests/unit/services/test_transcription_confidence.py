"""Unit tests for the transcription-confidence aggregator (research.md R1)."""

import math
from types import SimpleNamespace

from app.services.stt.confidence import (
    COMPRESSION_RATIO_THRESHOLD,
    NO_SPEECH_PROB_THRESHOLD,
    aggregate_confidence,
)


def segment(
    *,
    text: str = "hola mundo",
    start: float = 0.0,
    end: float = 1.0,
    avg_logprob: float = -0.2,
    no_speech_prob: float = 0.01,
    compression_ratio: float = 1.4,
    tokens: int = 4,
    temperature: float = 0.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        start=start,
        end=end,
        avg_logprob=avg_logprob,
        no_speech_prob=no_speech_prob,
        compression_ratio=compression_ratio,
        tokens=list(range(tokens)),
        temperature=temperature,
    )


class TestAggregation:
    def test_a_single_segment_is_the_exponential_of_its_logprob(self) -> None:
        result = aggregate_confidence([segment(avg_logprob=-0.2)])

        assert result == round(math.exp(-0.2), 6)

    def test_weights_by_token_count_not_duration(self) -> None:
        """A short segment with many tokens must not be discounted by its length."""
        segments = [
            segment(avg_logprob=-0.1, tokens=90, start=0.0, end=1.0),
            segment(avg_logprob=-2.0, tokens=10, start=1.0, end=9.0),
        ]

        result = aggregate_confidence(segments)

        expected = math.exp((-0.1 * 90 + -2.0 * 10) / 100)
        assert result == round(expected, 6)

    def test_duration_weighting_would_give_a_different_answer(self) -> None:
        """Guards the choice of weight, not merely the arithmetic."""
        segments = [
            segment(avg_logprob=-0.1, tokens=90, start=0.0, end=1.0),
            segment(avg_logprob=-2.0, tokens=10, start=1.0, end=9.0),
        ]

        by_duration = math.exp((-0.1 * 1.0 + -2.0 * 8.0) / 9.0)
        assert aggregate_confidence(segments) != round(by_duration, 6)

    def test_clean_speech_scores_well_above_the_default_threshold(self) -> None:
        assert aggregate_confidence([segment(avg_logprob=-0.15)]) > 0.55

    def test_mumbling_scores_below_the_default_threshold(self) -> None:
        assert aggregate_confidence([segment(avg_logprob=-0.9)]) < 0.55


class TestContentlessSegmentsAreExcluded:
    def test_empty_text_is_dropped(self) -> None:
        segments = [segment(avg_logprob=-0.2), segment(text="   ", avg_logprob=-3.0)]

        assert aggregate_confidence(segments) == round(math.exp(-0.2), 6)

    def test_zero_duration_is_dropped(self) -> None:
        segments = [segment(avg_logprob=-0.2), segment(start=2.0, end=2.0, avg_logprob=-3.0)]

        assert aggregate_confidence(segments) == round(math.exp(-0.2), 6)

    def test_negative_duration_is_dropped(self) -> None:
        segments = [segment(avg_logprob=-0.2), segment(start=3.0, end=1.0, avg_logprob=-3.0)]

        assert aggregate_confidence(segments) == round(math.exp(-0.2), 6)

    def test_a_silent_segment_is_dropped(self) -> None:
        noisy = segment(no_speech_prob=NO_SPEECH_PROB_THRESHOLD + 0.1, avg_logprob=-3.0)
        segments = [segment(avg_logprob=-0.2), noisy]

        assert aggregate_confidence(segments) == round(math.exp(-0.2), 6)

    def test_a_segment_exactly_at_the_silence_threshold_is_kept(self) -> None:
        """The rule is strictly greater-than, matching Whisper's own comparison."""
        segments = [segment(no_speech_prob=NO_SPEECH_PROB_THRESHOLD, avg_logprob=-0.2)]

        assert aggregate_confidence(segments) == round(math.exp(-0.2), 6)


class TestHallucinationOnSilence:
    def test_text_with_every_segment_silent_scores_zero(self) -> None:
        """Text transcribed from ranges Whisper calls silence is not trustworthy."""
        segments = [
            segment(text="Thank you for watching", no_speech_prob=0.95, avg_logprob=-0.05),
            segment(text="Thanks for watching", no_speech_prob=0.99, avg_logprob=-0.05),
        ]

        assert aggregate_confidence(segments) == 0.0

    def test_zero_is_below_the_default_threshold(self) -> None:
        segments = [segment(text="Thank you", no_speech_prob=0.95, avg_logprob=-0.05)]

        assert aggregate_confidence(segments) < 0.55


class TestRepetitionLoop:
    def test_a_high_compression_ratio_forces_low_confidence(self) -> None:
        """A repetition loop has an excellent avg_logprob — the model is sure of nonsense."""
        segments = [
            segment(
                text="no no no no no",
                avg_logprob=-0.02,
                compression_ratio=COMPRESSION_RATIO_THRESHOLD + 0.5,
            )
        ]

        assert aggregate_confidence(segments) == 0.0

    def test_one_looping_segment_condemns_the_whole_message(self) -> None:
        segments = [
            segment(avg_logprob=-0.1),
            segment(avg_logprob=-0.05, compression_ratio=COMPRESSION_RATIO_THRESHOLD + 1.0),
        ]

        assert aggregate_confidence(segments) == 0.0

    def test_a_ratio_at_the_threshold_is_not_a_loop(self) -> None:
        segments = [segment(avg_logprob=-0.2, compression_ratio=COMPRESSION_RATIO_THRESHOLD)]

        assert aggregate_confidence(segments) == round(math.exp(-0.2), 6)

    def test_a_loop_in_a_dropped_segment_is_ignored(self) -> None:
        """Only retained segments can condemn the message."""
        segments = [
            segment(avg_logprob=-0.2),
            segment(text="  ", compression_ratio=COMPRESSION_RATIO_THRESHOLD + 1.0),
        ]

        assert aggregate_confidence(segments) == round(math.exp(-0.2), 6)


class TestNoInformation:
    def test_no_segments_at_all_yields_none(self) -> None:
        assert aggregate_confidence([]) is None

    def test_empty_token_lists_yield_none_rather_than_a_division_error(self) -> None:
        assert aggregate_confidence([segment(tokens=0), segment(tokens=0)]) is None

    def test_none_is_distinct_from_zero(self) -> None:
        """NULL means 'no information'; 0.0 means 'heard, and not trustworthy'."""
        no_information = aggregate_confidence([])
        hallucination = aggregate_confidence([segment(text="hi", no_speech_prob=0.99)])

        assert no_information is None
        assert hallucination == 0.0


class TestResamplingIsNotAGate:
    def test_a_resampled_segment_is_still_scored(self) -> None:
        """temperature > 0 is logged, never gated on (research.md R1)."""
        segments = [segment(avg_logprob=-0.2, temperature=0.4)]

        assert aggregate_confidence(segments) == round(math.exp(-0.2), 6)
