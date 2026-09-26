"""T061: reading and classifying `claude` output against recorded fixture shapes (R-4, R-7)."""

import json

import pytest

from app.services.llm.claude_code.events import classify_failure, iter_text_deltas, parse_result
from app.services.llm.claude_code.failures import ClaudeCodeFailure, FailureKind
from tests.support.claude_fixtures import load_fixture_lines


def test_stream_yields_each_text_delta_and_ignores_other_events():
    deltas = list(iter_text_deltas(load_fixture_lines("stream_ok.ndjson")))

    assert deltas == ["¡Hola! ", "¿Adónde ", "viaja?"]


def test_json_result_is_the_result_text():
    assert parse_result(load_fixture_lines("json_ok.ndjson")) == "¡Hola! ¿Adónde viaja?"


def test_schema_result_is_the_structured_output_as_json_text():
    parsed = json.loads(parse_result(load_fixture_lines("schema_ok.ndjson")))

    assert parsed["verdict"] == "has_mistakes"
    assert len(parsed["corrections"]) == 2


@pytest.mark.parametrize(
    ("fixture", "kind"),
    [
        ("auth_failed.ndjson", FailureKind.NOT_SIGNED_IN),
        ("rate_limit_rejected.ndjson", FailureKind.USAGE_LIMIT),
        ("model_404.ndjson", FailureKind.MODEL_UNAVAILABLE),
        ("garbage.ndjson", FailureKind.UNEXPECTED_RESPONSE),
    ],
)
@pytest.mark.parametrize("reader", [parse_result, lambda lines: list(iter_text_deltas(lines))])
def test_failure_fixtures_raise_their_kind(fixture, kind, reader):
    with pytest.raises(ClaudeCodeFailure) as raised:
        reader(load_fixture_lines(fixture))

    assert raised.value.kind is kind


def test_output_without_a_result_line_is_unexpected():
    lines = load_fixture_lines("stream_ok.ndjson")[:-1]

    with pytest.raises(ClaudeCodeFailure) as raised:
        list(iter_text_deltas(lines))

    assert raised.value.kind is FailureKind.UNEXPECTED_RESPONSE


def test_an_assistant_rate_limit_error_is_a_usage_limit():
    failure = classify_failure({"type": "assistant", "error": "rate_limit"})

    assert failure.kind is FailureKind.USAGE_LIMIT


def test_any_other_error_result_is_unreachable():
    failure = classify_failure({"type": "result", "is_error": True, "result": "overloaded"})

    assert failure.kind is FailureKind.UNREACHABLE


def test_an_allowed_rate_limit_event_is_not_an_error():
    event = {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed"}}

    assert classify_failure(event) is None


def test_a_successful_result_is_not_an_error():
    assert classify_failure({"type": "result", "is_error": False, "result": "ok"}) is None
