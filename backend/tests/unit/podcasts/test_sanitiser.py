"""T018: a host line keeps only that host's words (research R4, FR-012)."""

import random

import pytest

from app.podcasts.catalog import PODCAST_FORMATS
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.line_address import LineAddress
from app.podcasts.services.sanitiser import (
    LineSanitiser,
    SanitisedLine,
    SentenceVerdict,
    StreamingSanitiser,
)
from app.podcasts.services.sentences import SentenceSplitter


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


# --- 011 T031: sanitising a streamed line one sentence at a time (research R13.4, R19.7) -----


LUCIA = Host("lead", "Lucía", "enthusiast", "es_AR-daniela-high", "host")
MARCO = Host("second", "Marco", "dry_sceptic", "es_ES-davefx-medium", "co_host")
CAST = Cast.for_format(PODCAST_FORMATS["panel"], LUCIA, MARCO)


def _streaming() -> StreamingSanitiser:
    address = LineAddress.for_episode(CAST, "Sam", "lead", "es", is_listening=False)
    return StreamingSanitiser(_lucia(), address)


def _stream(text: str, tokens: list[str] | None = None) -> tuple[list[str], StreamingSanitiser]:
    """Feed a line through the splitter and the sanitiser, as the line writer does."""
    splitter, sanitiser, kept = SentenceSplitter(), _streaming(), []
    for sentence in [s for t in (tokens or [text]) for s in splitter.feed(t)] + [splitter.flush()]:
        if not sentence:
            continue
        verdict = sanitiser.clean_sentence(sentence)
        if verdict.text:
            kept.append(verdict.text)
        if verdict.is_cut:
            break
    return kept, sanitiser


def test_the_first_sentence_loses_its_own_label():
    sanitiser = _streaming()

    assert sanitiser.clean_sentence("Lucía: ¡Hola a todos!") == SentenceVerdict(
        "¡Hola a todos!", False
    )
    assert sanitiser.clean_sentence("Lucía: otra vez.") == SentenceVerdict(
        "Lucía: otra vez.", False
    )
    assert sanitiser.was_trimmed is False


def test_every_sentence_loses_its_stage_directions():
    sanitiser = _streaming()

    assert sanitiser.clean_sentence("¡Qué rico! (ríe)") == SentenceVerdict("¡Qué rico!", False)
    assert sanitiser.was_trimmed is True


def test_a_sentence_in_another_speakers_voice_ends_the_line():
    sanitiser = _streaming()
    sanitiser.clean_sentence("¡Qué rica la paella!")

    assert sanitiser.clean_sentence("Marco: Yo no.") == SentenceVerdict("", True)
    assert sanitiser.was_trimmed is True


def test_an_address_tag_is_read_and_removed_without_a_trim():
    kept, sanitiser = _stream("Hoy hablamos de pan. ¿Y tú, comes pan? [@Sam]")

    assert kept == ["Hoy hablamos de pan.", "¿Y tú, comes pan?"]
    assert sanitiser.was_trimmed is False
    assert sanitiser.address().addressee == "learner"


def test_a_tag_on_its_own_line_gives_no_sentence():
    kept, sanitiser = _stream("Hoy hablamos de pan con Marco.\n[@Marco]")

    assert kept == ["Hoy hablamos de pan con Marco."]
    assert (sanitiser.address().addressee, sanitiser.address().is_from_tag) == ("second", True)


def test_a_tag_split_across_tokens_is_still_read():
    kept, sanitiser = _stream("", ["Hoy hablamos de pan. ¿Qué opinas? [@Mar", "co]"])

    assert kept == ["Hoy hablamos de pan.", "¿Qué opinas?"]
    assert sanitiser.address().addressee == "second"


SENTENCES = (
    "¡Qué rica la paella!",
    "Hoy hablamos de pan.",
    "¿Y tú qué piensas, Sam?",
    "Me encanta (ríe) la cocina.",
    "*suspira* Es verdad.",
    "Son 3.5 euros el kilo.",
    "Como dice Marco, hay que probar.",
)
LEAKS = ("Marco: Yo no.", "Sam: ¡Claro!", "Invitado: Me gusta.")


def _random_line(rng: random.Random) -> str:
    parts = rng.choices(SENTENCES, k=rng.randint(1, 5))
    if rng.random() < 0.3:
        parts.insert(rng.randint(1, len(parts)), rng.choice(LEAKS))
    if rng.random() < 0.3:
        parts.insert(0, "Lucía:")
    return " ".join(parts)


def _random_tokens(text: str, rng: random.Random) -> list[str]:
    cuts = sorted(rng.sample(range(1, len(text)), k=min(len(text) - 1, rng.randint(0, 10))))
    return [text[a:b] for a, b in zip([0, *cuts], [*cuts, len(text)], strict=True)]


@pytest.mark.parametrize("seed", range(300))
def test_streamed_sentences_join_to_the_whole_line_sanitised(seed):
    rng = random.Random(seed)
    line = _random_line(rng)

    kept, sanitiser = _stream(line, _random_tokens(line, rng))
    whole = _lucia().clean(line)

    assert "".join(" ".join(kept).split()) == "".join(whole.text.split())
    assert sanitiser.was_trimmed is whole.was_trimmed


@pytest.mark.parametrize("seed", range(100))
def test_no_kept_sentence_ever_holds_a_tag(seed):
    rng = random.Random(seed)
    tag = rng.choice(("[@Sam]", "[@Marco]", "[@all]", "\n[@all]"))
    line = f"{_random_line(rng)} {tag}"

    kept, _sanitiser = _stream(line, _random_tokens(line, rng))

    assert all("[@" not in sentence for sentence in kept)
