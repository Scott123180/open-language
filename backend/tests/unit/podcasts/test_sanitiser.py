"""T018: a host line keeps only that host's words (research R4, FR-012)."""

import pytest

from app.podcasts.services.sanitiser import LineSanitiser, SanitisedLine


def _lucia(learner_name: str | None = "Sam") -> LineSanitiser:
    return LineSanitiser.for_speaker("Lucía", ("Marco",), learner_name, "es")


@pytest.mark.parametrize(
    "text",
    ["Lucía: ¡Hola a todos!", "**Lucía:** ¡Hola a todos!", "[Lucía] ¡Hola a todos!"],
    ids=["plain", "bold", "bracketed"],
)
def test_the_speakers_own_label_is_stripped_without_counting_as_a_trim(text):
    assert _lucia().clean(text) == SanitisedLine("¡Hola a todos!", was_trimmed=False)


@pytest.mark.parametrize(
    "leak",
    [
        "Marco: Yo no estoy de acuerdo.",
        "**Marco:** Yo no estoy de acuerdo.",
        "Sam: Me gusta mucho.",
        "Guest: Me gusta.",
        "Learner: Me gusta.",
        "User: Me gusta.",
        "You: Me gusta.",
        "Invitado: Me gusta.",
    ],
)
def test_the_line_is_cut_where_another_participant_starts_speaking(leak):
    cleaned = _lucia().clean(f"¡Qué rica la paella! {leak}")

    assert cleaned == SanitisedLine("¡Qué rica la paella!", was_trimmed=True)


def test_a_leak_on_a_new_line_is_cut():
    cleaned = _lucia().clean("¡Qué rica la paella!\nMarco: Yo prefiero el cocido.")

    assert cleaned == SanitisedLine("¡Qué rica la paella!", was_trimmed=True)


def test_everything_after_the_first_leak_is_dropped():
    text = "Lucía: Hola. Marco: Hola. Lucía: ¿Qué tal?"

    assert _lucia().clean(text).text == "Hola."


@pytest.mark.parametrize(
    "text",
    ["¡Hola! (se ríe) ¿Qué tal?", "¡Hola! *risas* ¿Qué tal?", "¡Hola! [aplausos] ¿Qué tal?"],
    ids=["parenthesised", "starred", "bracketed"],
)
def test_stage_directions_are_dropped(text):
    assert _lucia().clean(text) == SanitisedLine("¡Hola! ¿Qué tal?", was_trimmed=True)


def test_a_line_that_is_only_a_label_is_empty():
    assert _lucia().clean("Marco: ¡Hola!").text == ""


def test_a_clean_line_is_returned_unchanged():
    text = "¡Qué rica la paella! ¿Tú qué opinas, Sam?"

    assert _lucia().clean(text) == SanitisedLine(text, was_trimmed=False)


@pytest.mark.parametrize(
    "text",
    ["Bueno, como dice Marco, la paella es un arte.", "Marco, ¿tú qué opinas?"],
    ids=["mid-sentence", "addressed"],
)
def test_naming_the_other_host_without_a_label_is_kept(text):
    assert _lucia().clean(text) == SanitisedLine(text, was_trimmed=False)


def test_without_a_learner_name_the_role_words_still_cut():
    cleaned = _lucia(learner_name=None).clean("Hola. Guest: Hola.")

    assert cleaned == SanitisedLine("Hola.", was_trimmed=True)


def test_labels_are_matched_without_regard_to_case():
    assert _lucia().clean("Hola. MARCO: Hola.").text == "Hola."


def test_german_guest_labels_are_known():
    marco = LineSanitiser.for_speaker("Jonas", ("Lena",), None, "de")

    assert marco.clean("Gut. Gast: Hallo!").text == "Gut."
