"""T007: the conversation-session value objects."""

import dataclasses
import hashlib

import pytest

from app.services.conversation import (
    SavedTurn,
    SessionFingerprint,
    SessionKey,
    SessionKind,
    TurnRequest,
)
from app.services.llm.selection_types import LLMSelection

_KEY = SessionKey(kind=SessionKind.ROLEPLAY, identifier="7")


def _fingerprint(**overrides) -> SessionFingerprint:
    values = {
        "selection": LLMSelection("ollama", "llama3.2"),
        "effort": "",
        "standing_prompt_digest": "abc",
    }
    return SessionFingerprint(**{**values, **overrides})


class TestSessionKey:
    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            _KEY.identifier = "8"  # type: ignore[misc]

    def test_is_hashable_and_equal_by_value(self):
        assert {_KEY: 1}[SessionKey(kind=SessionKind.ROLEPLAY, identifier="7")] == 1

    def test_kind_has_exactly_roleplay_helper_and_podcast(self):
        assert {kind.value for kind in SessionKind} == {"roleplay", "helper", "podcast"}

    def test_podcast_is_a_kind_of_session(self):
        assert SessionKind.PODCAST == "podcast"

    def test_a_podcast_key_is_hashable_and_distinct_from_the_roleplay_key(self):
        podcast = SessionKey(SessionKind.PODCAST, "57")
        roleplay = SessionKey(SessionKind.ROLEPLAY, "57")

        assert {podcast: 1, roleplay: 2}[podcast] == 1
        assert podcast != roleplay


class TestSavedTurn:
    def test_accepts_user_and_assistant(self):
        assert SavedTurn("m1", "user", "Hola").role == "user"
        assert SavedTurn("m2", "assistant", "¿Sí?").role == "assistant"

    def test_rejects_any_other_role(self):
        with pytest.raises(ValueError):
            SavedTurn("m1", "system", "You are…")


class TestSessionFingerprint:
    def test_equal_when_every_field_matches(self):
        assert _fingerprint() == _fingerprint()

    def test_differs_on_selection(self):
        assert _fingerprint() != _fingerprint(selection=LLMSelection("claude", "sonnet"))

    def test_differs_on_effort(self):
        assert _fingerprint() != _fingerprint(effort="low")

    def test_differs_on_prompt_digest(self):
        assert _fingerprint() != _fingerprint(standing_prompt_digest="def")

    def test_digest_prompt_is_sha256_hex(self):
        expected = hashlib.sha256("Eres Lucía.".encode()).hexdigest()

        assert SessionFingerprint.digest_prompt("Eres Lucía.") == expected


class TestTurnRequest:
    def _request(self, history, opening_instruction=None) -> TurnRequest:
        return TurnRequest(
            key=_KEY,
            standing_prompt="Eres Lucía.",
            history=tuple(history),
            guidance=None,
            opening_instruction=opening_instruction,
        )

    def test_opening_with_no_learner_turns_is_valid(self):
        request = self._request([], opening_instruction="Greet the learner.")

        assert request.opening_instruction == "Greet the learner."

    def test_history_ending_with_a_learner_turn_is_valid(self):
        history = [SavedTurn("m1", "assistant", "Hola"), SavedTurn("m2", "user", "Hola")]

        assert self._request(history).history[-1].role == "user"

    def test_opening_with_learner_turns_is_rejected(self):
        with pytest.raises(ValueError):
            self._request([SavedTurn("m1", "user", "Hola")], opening_instruction="Greet.")

    def test_history_ending_with_an_assistant_turn_is_rejected(self):
        with pytest.raises(ValueError):
            self._request([SavedTurn("m1", "user", "Hola"), SavedTurn("m2", "assistant", "¿Sí?")])

    def test_empty_history_without_an_opening_is_rejected(self):
        with pytest.raises(ValueError):
            self._request([])
