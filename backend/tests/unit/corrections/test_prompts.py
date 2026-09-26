"""Unit tests for the correction prompts (FR-007, FR-008, FR-009, FR-015)."""

from app.corrections.prompts import (
    CORRECTION_JSON_SCHEMA,
    build_evaluation_prompt,
    build_recast_instruction,
)


def _prompt() -> str:
    return build_evaluation_prompt(
        learner_text="Yo tener veinte años",
        target_language="Spanish",
        native_language="English",
        preceding_character_line="¿Cuántos años tienes?",
    )


class TestEvaluationPromptScope:
    def test_names_every_correctable_category(self) -> None:
        prompt = _prompt().lower()

        assert "conjugation" in prompt
        assert "agreement" in prompt
        assert "word choice" in prompt
        assert "word order" in prompt

    def test_rules_out_missing_diacritics(self) -> None:
        assert "diacritic" in _prompt().lower()

    def test_rules_out_regionally_valid_variation(self) -> None:
        assert "region" in _prompt().lower()

    def test_rules_out_phrasing_that_is_merely_unidiomatic(self) -> None:
        assert "unidiomatic" in _prompt().lower()

    def test_forbids_praise(self) -> None:
        assert "praise" in _prompt().lower()

    def test_caps_the_response_at_two_corrections(self) -> None:
        from app.corrections.config import MAX_CORRECTIONS_PER_MESSAGE

        assert str(MAX_CORRECTIONS_PER_MESSAGE) in _prompt()


class TestEvaluationPromptLanguages:
    def test_asks_for_the_explanation_in_the_native_language(self) -> None:
        prompt = _prompt()

        explanation_sentence = next(
            line for line in prompt.splitlines() if "explanation" in line.lower()
        )
        assert "English" in explanation_sentence

    def test_requires_corrected_text_in_the_target_language(self) -> None:
        prompt = _prompt()

        corrected_sentence = next(line for line in prompt.splitlines() if "corrected_text" in line)
        assert "Spanish" in corrected_sentence

    def test_includes_the_learner_text(self) -> None:
        assert "Yo tener veinte años" in _prompt()

    def test_includes_the_preceding_character_line_as_context(self) -> None:
        assert "¿Cuántos años tienes?" in _prompt()

    def test_omits_the_context_block_when_there_is_no_preceding_line(self) -> None:
        prompt = build_evaluation_prompt(
            learner_text="Yo tener veinte años",
            target_language="Spanish",
            native_language="English",
            preceding_character_line=None,
        )

        assert "Context" not in prompt


class TestVerdictGate:
    """The model states a verdict before listing anything (measured: halves false positives)."""

    def test_asks_for_a_verdict_first(self) -> None:
        prompt = _prompt()

        assert "verdict" in prompt
        assert prompt.index("verdict") < prompt.index("corrections")

    def test_says_an_empty_list_is_the_expected_answer(self) -> None:
        prompt = _prompt().lower()

        assert "most sentences" in prompt
        assert "empty list" in prompt

    def test_forbids_inventing_a_mistake_to_seem_helpful(self) -> None:
        assert "invent" in _prompt().lower()

    def test_rules_out_a_merely_different_but_valid_tense(self) -> None:
        assert "would also be correct" in _prompt().lower()


class TestCorrectionJsonSchema:
    def test_requires_a_verdict(self) -> None:
        assert "verdict" in CORRECTION_JSON_SCHEMA["required"]

    def test_the_verdict_is_constrained_to_two_values(self) -> None:
        assert set(CORRECTION_JSON_SCHEMA["properties"]["verdict"]["enum"]) == {
            "correct",
            "has_mistakes",
        }

    def test_declares_a_corrections_array(self) -> None:
        assert CORRECTION_JSON_SCHEMA["properties"]["corrections"]["type"] == "array"

    def test_each_correction_requires_every_rendered_field(self) -> None:
        required = CORRECTION_JSON_SCHEMA["properties"]["corrections"]["items"]["required"]

        assert set(required) == {"category", "error_fragment", "corrected_text", "explanation"}

    def test_category_is_constrained_to_the_known_categories(self) -> None:
        items = CORRECTION_JSON_SCHEMA["properties"]["corrections"]["items"]

        assert set(items["properties"]["category"]["enum"]) == {
            "conjugation",
            "agreement",
            "word_choice",
            "word_order",
        }


class TestRecastInstruction:
    def _instruction(self) -> str:
        return build_recast_instruction("Yo tengo veinte años", "Spanish")

    def test_carries_the_corrected_form(self) -> None:
        assert "Yo tengo veinte años" in self._instruction()

    def test_never_requests_native_language_output(self) -> None:
        instruction = self._instruction().lower()

        assert "english" not in instruction
        assert "native language" not in instruction

    def test_requires_the_reply_to_stay_in_the_target_language(self) -> None:
        assert "Spanish" in self._instruction()

    def test_instructs_a_natural_restatement_rather_than_a_correction(self) -> None:
        instruction = self._instruction().lower()

        assert "naturally" in instruction
        assert "do not point out" in instruction
        assert "do not explain" in instruction

    def test_forbids_asking_the_learner_to_repeat(self) -> None:
        assert "repeat" in self._instruction().lower()

    def test_appending_it_leaves_the_critical_language_rule_at_the_head(self) -> None:
        """The suffix is appended, so the roleplay prompt's opening rule still leads."""
        from app.prompts.templates import build_roleplay_system_prompt

        system_prompt = build_roleplay_system_prompt(
            scenario_title="Cafe",
            scenario_description="ordering coffee",
            character_description="You are a barista.",
            target_language="Spanish",
            native_language="English",
        )

        combined = system_prompt + self._instruction()

        assert combined.startswith("CRITICAL LANGUAGE RULE")
        assert "CRITICAL LANGUAGE RULE" in combined
