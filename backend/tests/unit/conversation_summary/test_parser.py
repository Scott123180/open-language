"""T075: parsing the model's structured summary (contracts §9)."""

import json

import pytest

from app.conversation_summary.services.summariser import (
    SummaryPoint,
    SummaryUnavailableError,
    parse_points,
)
from app.services.llm.base import LLMError


def _reply(points) -> str:
    return json.dumps({"points": points})


def _point(index: int) -> dict:
    return {"conversation_language": f"Punto {index}.", "english": f"Point {index}."}


@pytest.mark.parametrize("count", [1, 3, 5])
def test_one_to_five_points_each_in_both_languages_are_read(count):
    points = parse_points(_reply([_point(i) for i in range(count)]))

    assert points == tuple(SummaryPoint(f"Punto {i}.", f"Point {i}.") for i in range(count))


@pytest.mark.parametrize(
    "reply",
    [
        _reply([]),
        _reply([_point(i) for i in range(6)]),
        _reply([{"conversation_language": "Solo uno."}]),
        _reply([{"conversation_language": "", "english": "Blank"}]),
        "{not json",
        json.dumps({"summary": "wrong shape"}),
    ],
    ids=["none", "six", "missing-english", "blank", "malformed", "wrong-shape"],
)
def test_an_unusable_reply_is_a_retryable_provider_error(reply):
    with pytest.raises(SummaryUnavailableError) as raised:
        parse_points(reply)

    assert isinstance(raised.value, LLMError)
    assert "try again" in raised.value.user_message.lower()
