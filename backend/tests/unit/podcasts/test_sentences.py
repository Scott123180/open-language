"""011 T030: SentenceSplitter, tokens in, complete sentences out (research R13.3)."""

import random

import pytest

from app.podcasts.services.sentences import SentenceSplitter


def split_whole(text: str) -> list[str]:
    splitter = SentenceSplitter()
    return [*splitter.feed(text), *_flushed(splitter)]


def split_tokens(tokens: list[str]) -> list[str]:
    splitter = SentenceSplitter()
    sentences = [sentence for token in tokens for sentence in splitter.feed(token)]
    return [*sentences, *_flushed(splitter)]


def _flushed(splitter: SentenceSplitter) -> list[str]:
    rest = splitter.flush()
    return [rest] if rest else []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hola a todos. Hoy hablamos de pan.", ["Hola a todos.", "Hoy hablamos de pan."]),
        ("¡Qué bien, amigos! ¿Y tú, Scott?", ["¡Qué bien, amigos!", "¿Y tú, Scott?"]),
        ("Me gusta mucho. ¿Y a ti?", ["Me gusta mucho.", "¿Y a ti?"]),
        ("Me gusta mucho. ¡Claro que sí!", ["Me gusta mucho.", "¡Claro que sí!"]),
        ("Es la hora del té… Ahora hablamos.", ["Es la hora del té…", "Ahora hablamos."]),
        ('Ella dijo "hola a todos." Luego se fue.', ['Ella dijo "hola a todos."', "Luego se fue."]),
        ("Hay pan (mucho pan.) Luego comemos.", ["Hay pan (mucho pan.)", "Luego comemos."]),
        ("Son las ocho de la tarde. 20 personas llegan.", ["Son las ocho de la tarde.", "20 personas llegan."]),
        ('Pregunta muy buena. "Sí", dice ella.', ["Pregunta muy buena.", '"Sí", dice ella.']),
    ],
)
def test_a_sentence_ends_at_its_punctuation_before_a_new_sentence(text, expected):
    assert split_whole(text) == expected


def test_a_newline_always_ends_a_sentence():
    assert split_whole("Hoy hablamos de pan\nEl pan es muy bueno.") == [
        "Hoy hablamos de pan",
        "El pan es muy bueno.",
    ]


@pytest.mark.parametrize(
    "text",
    ["El café cuesta 3.5 euros hoy.", "¿Sí? sí, claro que sí, amigos.", "Hola, amigos. bueno, ya está."],
)
def test_there_is_no_boundary_inside_a_number_or_before_a_lower_case_word(text):
    assert split_whole(text) == [text]


def test_a_short_sentence_joins_the_next():
    assert split_whole("Sr. Pérez llega tarde. Luego comemos.") == [
        "Sr. Pérez llega tarde.",
        "Luego comemos.",
    ]


def test_an_address_tag_stays_with_the_last_sentence():
    assert split_whole("Hoy hablamos de pan. ¿Y tú? [@Scott]") == [
        "Hoy hablamos de pan.",
        "¿Y tú? [@Scott]",
    ]


def test_flush_gives_the_rest_or_nothing():
    splitter = SentenceSplitter()

    assert splitter.feed("Hola a todos. Hoy") == ["Hola a todos."]
    assert splitter.flush() == "Hoy"
    assert splitter.flush() == ""


def test_a_sentence_waits_until_the_next_one_starts():
    splitter = SentenceSplitter()

    assert splitter.feed("Hola a todos.") == []
    assert splitter.feed(" ") == []
    assert splitter.feed("Hoy") == ["Hola a todos."]


SCRIPTS = {
    "es": ("¿Qué tal, Scott?", "Hoy hablamos de pan.", "¡Qué rico es!", "Son 3.5 euros.",
           "Sr. Pérez llega.", "El té… es bueno.", '"Sí", dice ella.'),
    "de": ("Wie geht's, Scott?", "Heute reden wir über Brot.", "Das ist lecker!",
           "Es kostet 3.5 Euro.", "Über Brot sprechen wir.", "Ähm, ja."),
    "it": ("Come stai, Scott?", "Oggi parliamo del pane.", "È buonissimo!", "Ciao a tutti.",
           "Più tardi mangiamo.", "Sì, certo."),
}


def _random_text(rng: random.Random) -> str:
    sentences = rng.choices(SCRIPTS[rng.choice(list(SCRIPTS))], k=rng.randint(1, 7))
    separators = [rng.choice((" ", "  ", "\n", " ")) for _ in sentences]
    return "".join(f"{sentence}{gap}" for sentence, gap in zip(sentences, separators, strict=True))


def _random_split(text: str, rng: random.Random) -> list[str]:
    cuts = sorted(rng.sample(range(1, len(text)), k=min(len(text) - 1, rng.randint(0, 12))))
    return [text[start:end] for start, end in zip([0, *cuts], [*cuts, len(text)], strict=True)]


@pytest.mark.parametrize("seed", range(300))
def test_any_split_into_tokens_gives_the_same_sentences(seed):
    rng = random.Random(seed)
    text = _random_text(rng)

    assert split_tokens(_random_split(text, rng)) == split_whole(text)
