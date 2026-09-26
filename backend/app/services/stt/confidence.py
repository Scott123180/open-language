"""Transcription confidence aggregation (research.md R1).

Three steps: drop segments carrying no speech, force low confidence when a
retained segment shows a repetition loop, then take the token-weighted mean of
the per-token log-probabilities and map it back into 0–1.
"""

import logging
import math
from collections.abc import Iterable

logger = logging.getLogger(__name__)

# Whisper's own ``no_speech_threshold`` default: above this the range is silence.
NO_SPEECH_PROB_THRESHOLD = 0.6

# Whisper's own ``compression_ratio_threshold`` default: above this the decode
# has fallen into a repetition loop and its high confidence is meaningless.
COMPRESSION_RATIO_THRESHOLD = 2.4

_HALLUCINATION_ON_SILENCE = 0.0
_PRECISION = 6


def aggregate_confidence(segments: Iterable[object]) -> float | None:
    """Return 0.0–1.0, or None when there is no confidence information at all.

    None and 0.0 are different answers: None means nothing was heard to judge,
    while 0.0 means words were transcribed from ranges that are not trustworthy.
    """
    all_segments = list(segments)
    if not all_segments:
        return None

    spoken = [segment for segment in all_segments if _carries_speech(segment)]
    if not spoken:
        # Text exists but every range read as silence — hallucination-on-silence.
        return _HALLUCINATION_ON_SILENCE
    if any(_is_repetition_loop(segment) for segment in spoken):
        return _HALLUCINATION_ON_SILENCE

    return _token_weighted_confidence(spoken)


def _carries_speech(segment) -> bool:
    if not segment.text.strip():
        return False
    if segment.end - segment.start <= 0:
        return False
    return segment.no_speech_prob <= NO_SPEECH_PROB_THRESHOLD


def _is_repetition_loop(segment) -> bool:
    """A loop ("no no no no…") scores an excellent avg_logprob on nonsense."""
    return segment.compression_ratio > COMPRESSION_RATIO_THRESHOLD


def _token_weighted_confidence(segments: list) -> float | None:
    """avg_logprob is already a per-token mean, so recombine by token count."""
    total_tokens = 0
    weighted_logprob = 0.0
    for segment in segments:
        token_count = len(segment.tokens)
        if segment.temperature > 0:
            logger.debug("Segment decoded at temperature %s", segment.temperature)
        total_tokens += token_count
        weighted_logprob += segment.avg_logprob * token_count

    if total_tokens == 0:
        return None
    return round(math.exp(weighted_logprob / total_tokens), _PRECISION)
