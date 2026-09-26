"""T063: ClaudeCodeSession — one long-lived process per conversation (research R-14)."""

import pytest

from app.config import Settings
from app.services.conversation import SavedTurn, SessionKey, SessionKind
from app.services.llm.claude_code.failures import ClaudeCodeFailure, FailureKind
from app.services.llm.claude_code.provider import ClaudeCodeLLMProvider
from app.services.llm.claude_code.session import TURN_GUIDANCE_PARAGRAPH
from app.services.llm.claude_code.transcript import render_guidance_block, render_rebuild_turn
from tests.support.claude_fixtures import load_fixture_lines
from tests.support.fake_availability import FakeAvailability, unavailable
from tests.support.scripted_claude_runner import ScriptedClaudeCodeRunner

STANDING = "Eres Lucía, taquillera."
KEY = SessionKey(SessionKind.ROLEPLAY, "7")
GREETING = SavedTurn("m1", "assistant", "¡Buenos días!")
SECOND_LINE = SavedTurn("m2", "assistant", "¿Adónde viaja?")
ASK = SavedTurn("m3", "user", "A Sevilla.")
RETRY = SavedTurn("m4", "user", "A Sevilla, por favor.")


@pytest.fixture()
def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        claude_executable="/opt/claude",
        claude_log_dir=tmp_path / "claude-logs",
        claude_workdir=tmp_path / "claude-workdir",
        claude_request_timeout_seconds=90.0,
    )


@pytest.fixture()
def runner() -> ScriptedClaudeCodeRunner:
    return ScriptedClaudeCodeRunner()


@pytest.fixture()
def availability() -> FakeAvailability:
    return FakeAvailability()


@pytest.fixture()
def provider(runner, availability, settings) -> ClaudeCodeLLMProvider:
    return ClaudeCodeLLMProvider(runner, availability, settings, "sonnet", "medium")


def _flag(argv: list[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


def _sent(runner) -> list[dict]:
    return runner.processes[0].sent_messages


def _user_contents(runner) -> list[str]:
    return [m["message"]["content"] for m in _sent(runner) if m["type"] == "user"]


def test_warm_spawns_the_process_and_writes_nothing(provider, runner):
    provider.open_session(KEY, STANDING, [GREETING, ASK]).warm()

    assert len(runner.spawns) == 1
    assert runner.processes[0].sent_lines == []


def test_history_without_learner_turns_is_seeded_natively(provider, runner):
    session = provider.open_session(KEY, STANDING, [GREETING, SECOND_LINE])

    "".join(session.reply([ASK], None))

    assert _sent(runner) == [
        {"type": "assistant", "message": {"role": "assistant", "content": "¡Buenos días!"}},
        {"type": "assistant", "message": {"role": "assistant", "content": "¿Adónde viaja?"}},
        {"type": "user", "message": {"role": "user", "content": "A Sevilla."}},
    ]


def test_history_with_learner_turns_is_rebuilt_in_one_user_line(provider, runner):
    history = [GREETING, ASK, SECOND_LINE]
    session = provider.open_session(KEY, STANDING, history)

    "".join(session.reply([RETRY], None))

    assert _user_contents(runner) == [render_rebuild_turn(history, [RETRY], None)]
    assert len(runner.read_timeouts) == 1


def test_rebuild_of_long_history_generates_exactly_once(provider, runner):
    history = [
        SavedTurn(f"m{index}", "assistant" if index % 2 else "user", f"turn {index}")
        for index in range(20)
    ]
    session = provider.open_session(KEY, STANDING, history)

    "".join(session.reply([SavedTurn("m20", "user", "¿Y ahora?")], None))

    assert len(runner.read_timeouts) == 1
    assert len(_user_contents(runner)) == 1


def test_later_turns_are_native_single_lines(provider, runner):
    session = provider.open_session(KEY, STANDING, [GREETING, ASK, SECOND_LINE])
    "".join(session.reply([RETRY], None))
    session.acknowledge("m5")

    "".join(session.reply([SavedTurn("m6", "user", "Gracias.")], None))

    assert _user_contents(runner)[-1] == "Gracias."


def test_several_pending_turns_merge_into_one_user_line(provider, runner):
    session = provider.open_session(KEY, STANDING, [GREETING])

    "".join(session.reply([ASK, RETRY], None))

    assert _user_contents(runner) == ["A Sevilla.\nA Sevilla, por favor."]


def test_guidance_travels_inside_that_turns_user_line(provider, runner):
    session = provider.open_session(KEY, STANDING, [GREETING])

    "".join(session.reply([ASK], "Recast gently."))

    assert _user_contents(runner) == [f"A Sevilla.\n\n{render_guidance_block('Recast gently.')}"]


def test_the_standing_prompt_ends_with_the_turn_guidance_paragraph(provider, runner):
    provider.open_session(KEY, STANDING, [GREETING]).warm()

    system_prompt = _flag(runner.spawns[0][0], "--system-prompt")
    assert system_prompt.startswith(STANDING)
    assert system_prompt.endswith(TURN_GUIDANCE_PARAGRAPH)
    assert "turn_guidance" in TURN_GUIDANCE_PARAGRAPH


def test_the_session_uses_the_learners_effort(provider, runner):
    provider.open_session(KEY, STANDING, [GREETING]).warm()

    assert _flag(runner.spawns[0][0], "--effort") == "medium"
    assert _flag(runner.spawns[0][0], "--input-format") == "stream-json"


def test_stderr_is_logged_per_session_outside_the_workdir(provider, runner, settings):
    provider.open_session(KEY, STANDING, [GREETING]).warm()

    assert runner.spawns[0][1] == settings.claude_log_dir / "session-roleplay-7.log"


def test_turns_read_with_the_request_deadline(provider, runner):
    session = provider.open_session(KEY, STANDING, [GREETING])

    "".join(session.reply([ASK], None))

    assert runner.read_timeouts == [90.0]


def test_the_reply_is_the_text_deltas(provider, runner):
    runner.session_turns = [load_fixture_lines("session_three_turns.ndjson")[:3]]
    session = provider.open_session(KEY, STANDING, [GREETING])

    assert "".join(session.reply([ASK], None)) == "Buenos días."


def test_opening_reply_is_not_recorded_as_a_turn(provider, runner):
    session = provider.open_session(KEY, STANDING, [])

    "".join(session.reply_to_opening("Greet the learner."))
    session.acknowledge("m1")

    assert _user_contents(runner) == ["Greet the learner."]
    assert list(session.synced_turn_ids) == ["m1"]


class TestPreFlight:
    def test_runs_once_at_spawn_not_on_later_turns(self, provider, availability):
        session = provider.open_session(KEY, STANDING, [GREETING])
        session.warm()
        "".join(session.reply([ASK], None))
        session.acknowledge("m5")

        "".join(session.reply([SavedTurn("m6", "user", "Gracias.")], None))

        assert availability.checks == 1

    def test_the_first_reply_spawns_when_not_warmed(self, provider, availability, runner):
        "".join(provider.open_session(KEY, STANDING, [GREETING]).reply([ASK], None))

        assert (availability.checks, len(runner.spawns)) == (1, 1)

    def test_a_failing_check_refuses_without_spawning(self, provider, availability, runner):
        availability.answer = unavailable("not_signed_in")

        with pytest.raises(ClaudeCodeFailure) as raised:
            provider.open_session(KEY, STANDING, [GREETING]).warm()

        assert raised.value.kind is FailureKind.NOT_SIGNED_IN
        assert raised.value.can_retry is False
        assert runner.spawns == []


class TestFailures:
    def test_a_dead_process_breaks_the_session_and_can_retry(self, provider, runner):
        session = provider.open_session(KEY, STANDING, [GREETING])
        session.warm()
        runner.is_dead = True

        with pytest.raises(ClaudeCodeFailure) as raised:
            "".join(session.reply([ASK], None))

        assert raised.value.kind is FailureKind.UNREACHABLE
        assert raised.value.can_retry is True
        assert session.is_broken is True

    def test_an_auth_failure_mid_session_cannot_retry(self, provider, runner):
        runner.session_turns = [load_fixture_lines("auth_failed.ndjson")]
        session = provider.open_session(KEY, STANDING, [GREETING])

        with pytest.raises(ClaudeCodeFailure) as raised:
            "".join(session.reply([ASK], None))

        assert raised.value.can_retry is False
        assert session.is_broken is True


def test_fingerprint_carries_the_learners_effort(provider):
    fingerprint = provider.session_fingerprint(STANDING)

    assert fingerprint.effort == "medium"
    assert (fingerprint.selection.provider_id, fingerprint.selection.model) == ("claude", "sonnet")


def test_close_closes_the_process(provider, runner):
    session = provider.open_session(KEY, STANDING, [GREETING])
    session.warm()

    session.close()

    assert runner.processes[0].close_count == 1
