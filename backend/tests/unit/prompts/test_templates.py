from app.prompts.templates import (
    build_grammar_prompt,
    build_helper_system_prompt,
    build_phrasing_prompt,
    build_roleplay_system_prompt,
    build_suggestion_prompt,
    build_translation_prompt,
    build_word_lookup_prompt,
)


def test_build_roleplay_system_prompt_contains_target_language() -> None:
    result = build_roleplay_system_prompt(
        scenario_title="Buy a Ticket",
        scenario_description="Purchase a train ticket.",
        character_description="a ticket agent",
        target_language="Spanish",
        native_language="English",
    )
    assert "Spanish" in result


def test_build_roleplay_system_prompt_contains_redirect_rule() -> None:
    result = build_roleplay_system_prompt(
        scenario_title="Buy a Ticket",
        scenario_description="Purchase a train ticket.",
        character_description="a ticket agent",
        target_language="Spanish",
        native_language="English",
    )
    assert "Por favor" in result or "respond" in result.lower()
    assert "Spanish" in result


def test_build_grammar_prompt_contains_message_content() -> None:
    content = "Yo fue al mercado ayer."
    result = build_grammar_prompt(content, "English")
    assert content in result


def test_build_translation_prompt_contains_native_language() -> None:
    result = build_translation_prompt("Hola, ¿cómo estás?", "English")
    assert "English" in result


def test_build_phrasing_prompt_contains_target_language() -> None:
    result = build_phrasing_prompt("I want to buy a ticket.", "Spanish")
    assert "Spanish" in result


def test_build_word_lookup_prompt_contains_word() -> None:
    result = build_word_lookup_prompt("madrugada", "Spanish", "English")
    assert "madrugada" in result


def test_build_suggestion_prompt_contains_target_language_and_n() -> None:
    history = "User: Hola\nAssistant: ¡Hola! ¿Cómo puedo ayudarte?"
    result = build_suggestion_prompt(history, "Spanish", 3)
    assert "Spanish" in result
    assert "3" in result


def test_build_helper_system_prompt_contains_languages() -> None:
    result = build_helper_system_prompt("Spanish", "English")
    assert "Spanish" in result
    assert "English" in result


# ---- Additional coverage for T080 ----


def test_build_word_lookup_prompt_contains_target_language() -> None:
    result = build_word_lookup_prompt("madrugada", "Spanish", "English")
    assert "Spanish" in result


def test_build_word_lookup_prompt_contains_native_language() -> None:
    result = build_word_lookup_prompt("madrugada", "Spanish", "English")
    assert "English" in result


def test_build_word_lookup_prompt_includes_sentence_context_when_provided() -> None:
    result = build_word_lookup_prompt("hambre", "Spanish", "English", "Tengo mucha hambre hoy.")
    assert "Tengo mucha hambre hoy." in result


def test_build_word_lookup_prompt_omits_context_clause_when_none() -> None:
    result = build_word_lookup_prompt("hambre", "Spanish", "English", None)
    assert "as used in the sentence" not in result


def test_build_suggestion_prompt_contains_history_text() -> None:
    history = "User: Hola\nAssistant: ¡Hola! ¿Cómo puedo ayudarte?"
    result = build_suggestion_prompt(history, "Spanish", 2)
    assert history in result


def test_build_grammar_prompt_contains_native_language() -> None:
    result = build_grammar_prompt("Yo fue al mercado.", "English")
    assert "English" in result


def test_build_translation_prompt_contains_message_content() -> None:
    content = "Hola, ¿cómo estás?"
    result = build_translation_prompt(content, "English")
    assert content in result


def test_build_phrasing_prompt_contains_message_content() -> None:
    content = "I want to buy a ticket."
    result = build_phrasing_prompt(content, "Spanish")
    assert content in result
