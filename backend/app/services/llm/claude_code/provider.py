"""ClaudeCodeLLMProvider: the learner's signed-in `claude -p`, as a plain chat model.

One-shot calls use fixed effort levels (research R-6); conversation sessions use the learner's.
Every call first confirms Claude Code is signed in with a Claude plan, so no prompt is ever
billed to an API account (FR-010a).
"""

from collections.abc import Iterator, Sequence
from contextlib import closing
from dataclasses import dataclass

from app.config import Settings
from app.services.conversation.session import (
    ConversationSession,
    SavedTurn,
    SessionCapableProvider,
    SessionFingerprint,
    SessionKey,
)
from app.services.llm.availability import ProviderAvailabilityChecker
from app.services.llm.base import ChatMessage, LLMProvider, StructuredLLMProvider
from app.services.llm.catalog import CLAUDE_PROVIDER_ID
from app.services.llm.claude_code.command import (
    ClaudeRequest,
    ClaudeSessionRequest,
    OutputMode,
    build_claude_argv,
    build_session_argv,
)
from app.services.llm.claude_code.events import iter_text_deltas, parse_result
from app.services.llm.claude_code.failures import failure_for_availability
from app.services.llm.claude_code.runner import ClaudeCodeRunner
from app.services.llm.claude_code.session import (
    TURN_GUIDANCE_PARAGRAPH,
    ClaudeCodeSession,
    ClaudeSessionConfig,
    session_log_path,
)
from app.services.llm.claude_code.transcript import render_prompt
from app.services.llm.selection_types import EFFORT_LOW, EFFORT_MEDIUM, LLMSelection

ONE_SHOT_EFFORT = EFFORT_LOW
# Corrections are where judgement matters: false flags are why 003 shipped as experimental.
STRUCTURED_EFFORT = EFFORT_MEDIUM


@dataclass(frozen=True, slots=True)
class _OneShot:
    mode: OutputMode
    effort: str
    timeout_seconds: float
    schema: dict | None = None


class ClaudeCodeLLMProvider(LLMProvider, StructuredLLMProvider, SessionCapableProvider):
    def __init__(
        self,
        runner: ClaudeCodeRunner,
        availability: ProviderAvailabilityChecker,
        settings: Settings,
        model: str,
        effort: str,
    ) -> None:
        self._runner = runner
        self._availability = availability
        self._settings = settings
        self._model = model
        self._effort = effort

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def runner(self) -> ClaudeCodeRunner:
        return self._runner

    @property
    def availability(self) -> ProviderAvailabilityChecker:
        return self._availability

    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        call = _OneShot(OutputMode.STREAM, ONE_SHOT_EFFORT, self._request_timeout)
        with closing(self._run(messages, call)) as lines:
            yield from iter_text_deltas(lines)

    def chat(self, messages: list[ChatMessage]) -> str:
        call = _OneShot(OutputMode.JSON, ONE_SHOT_EFFORT, self._request_timeout)
        with closing(self._run(messages, call)) as lines:
            return parse_result(lines)

    def chat_json(self, messages: list[ChatMessage], schema: dict) -> str:
        # The structured deadline is the correction budget: its only client is corrections,
        # so a correction that runs out of time has its process killed, not left running.
        timeout = self._settings.correction_timeout_seconds
        call = _OneShot(OutputMode.SCHEMA, STRUCTURED_EFFORT, timeout, schema)
        with closing(self._run(messages, call)) as lines:
            return parse_result(lines)

    def session_fingerprint(self, standing_prompt: str) -> SessionFingerprint:
        selection = LLMSelection(CLAUDE_PROVIDER_ID, self._model)
        digest = SessionFingerprint.digest_prompt(standing_prompt)
        return SessionFingerprint(selection, self._effort, digest)

    def open_session(
        self, key: SessionKey, standing_prompt: str, history: Sequence[SavedTurn]
    ) -> ConversationSession:
        request = ClaudeSessionRequest(
            executable=self._settings.claude_executable,
            model=self._model,
            effort=self._effort,
            system_prompt=f"{standing_prompt}\n\n{TURN_GUIDANCE_PARAGRAPH}",
        )
        config = ClaudeSessionConfig(
            runner=self._runner,
            availability=self._availability,
            argv=tuple(build_session_argv(request)),
            log_path=session_log_path(self._settings.claude_log_dir, key),
            turn_timeout_seconds=self._request_timeout,
            fingerprint=self.session_fingerprint(standing_prompt),
        )
        return ClaudeCodeSession(config, history)

    @property
    def _request_timeout(self) -> float:
        return self._settings.claude_request_timeout_seconds

    def _run(self, messages: list[ChatMessage], call: _OneShot) -> Iterator[str]:
        self._ensure_on_plan()
        rendered = render_prompt(messages)
        request = ClaudeRequest(
            executable=self._settings.claude_executable,
            model=self._model,
            effort=call.effort,
            system_prompt=rendered.system_prompt,
            output_mode=call.mode,
            json_schema=call.schema,
        )
        argv = build_claude_argv(request)
        return self._runner.stream_lines(argv, rendered.prompt, call.timeout_seconds)

    def _ensure_on_plan(self) -> None:
        """The FR-010a pre-flight: refuse before any prompt is sent."""
        availability = self._availability.check()
        if not availability.is_available:
            raise failure_for_availability(availability.reason)
