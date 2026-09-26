"""Reading `claude`'s newline-delimited JSON output (research R-4, R-7).

Only the fields listed in contracts/api.md §3 are read. Unknown event types are ignored, so new
Claude Code event types don't break parsing. A line that isn't JSON is skipped; output that never
reaches a result line is an unexpected response.
"""

import json
from collections.abc import Iterable, Iterator

from app.services.llm.claude_code.failures import ClaudeCodeFailure, FailureKind

RESULT_EVENT_TYPE = "result"
STREAM_EVENT_TYPE = "stream_event"
ASSISTANT_EVENT_TYPE = "assistant"
RATE_LIMIT_EVENT_TYPE = "rate_limit_event"
TEXT_DELTA_TYPE = "text_delta"
AUTHENTICATION_FAILED = "authentication_failed"
RATE_LIMITED = "rate_limit"
RATE_LIMIT_REJECTED = "rejected"
MODEL_NOT_FOUND_STATUS = 404
_NO_RESULT_DETAIL = "claude produced no result line"


def iter_text_deltas(lines: Iterable[str]) -> Iterator[str]:
    """Yield each reply fragment. Raises ClaudeCodeFailure on a failure event or no result."""
    for event in _checked_events(lines):
        if event.get("type") == RESULT_EVENT_TYPE:
            return
        text = _text_delta(event)
        if text:
            yield text
    raise ClaudeCodeFailure(FailureKind.UNEXPECTED_RESPONSE, _NO_RESULT_DETAIL)


def parse_result(lines: Iterable[str]) -> str:
    """The result text; for schema calls, the validated `structured_output` as JSON text."""
    for event in _checked_events(lines):
        if event.get("type") != RESULT_EVENT_TYPE:
            continue
        if "structured_output" in event:
            return json.dumps(event["structured_output"], ensure_ascii=False)
        return str(event.get("result", ""))
    raise ClaudeCodeFailure(FailureKind.UNEXPECTED_RESPONSE, _NO_RESULT_DETAIL)


def classify_failure(event: dict) -> ClaudeCodeFailure | None:
    event_type = event.get("type")
    if event_type == ASSISTANT_EVENT_TYPE:
        return _assistant_failure(event)
    if event_type == RATE_LIMIT_EVENT_TYPE:
        status = (event.get("rate_limit_info") or {}).get("status")
        if status == RATE_LIMIT_REJECTED:
            return ClaudeCodeFailure(FailureKind.USAGE_LIMIT, "Rate limit event: rejected")
    if event_type == RESULT_EVENT_TYPE and event.get("is_error"):
        return _result_failure(event)
    return None


def is_result_line(line: str) -> bool:
    """True for the line that ends a turn, whether it succeeded or failed."""
    event = _decode(line)
    return event is not None and event.get("type") == RESULT_EVENT_TYPE


def _checked_events(lines: Iterable[str]) -> Iterator[dict]:
    """Decoded events, raising at the first one that reports a failure."""
    for line in lines:
        event = _decode(line)
        if event is None:
            continue
        failure = classify_failure(event)
        if failure is not None:
            raise failure
        yield event


def _assistant_failure(event: dict) -> ClaudeCodeFailure | None:
    # Claude Code puts the error on the assistant event; read the message too, to be safe.
    error = event.get("error") or (event.get("message") or {}).get("error")
    if error == AUTHENTICATION_FAILED:
        return ClaudeCodeFailure(FailureKind.NOT_SIGNED_IN, "Assistant error: authentication")
    if error == RATE_LIMITED:
        return ClaudeCodeFailure(FailureKind.USAGE_LIMIT, "Assistant error: rate limit")
    return None


def _result_failure(event: dict) -> ClaudeCodeFailure:
    detail = f"Error result: {event.get('result', '')!s}"[:200]
    if event.get("api_error_status") == MODEL_NOT_FOUND_STATUS:
        return ClaudeCodeFailure(FailureKind.MODEL_UNAVAILABLE, detail)
    return ClaudeCodeFailure(FailureKind.UNREACHABLE, detail)


def _text_delta(event: dict) -> str | None:
    if event.get("type") != STREAM_EVENT_TYPE:
        return None
    delta = (event.get("event") or {}).get("delta") or {}
    return delta.get("text") if delta.get("type") == TEXT_DELTA_TYPE else None


def _decode(line: str) -> dict | None:
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    return event if isinstance(event, dict) else None
