"""011 T031a: LineAddress, who a written host line is for (research R19.3, data-model §3.7)."""

import pytest

from app.podcasts.catalog import ADDRESS_TAG_MAX_LENGTH, PODCAST_FORMATS
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.line_address import LineAddress, LineAddressResult

HUGO = Host("lead", "Hugo", "curious_interviewer", "es_ES-davefx-medium", "host")
JULIA = Host("second", "Julia", "expert", "es_AR-daniela-high", "co_host")
PANEL = Cast.for_format(PODCAST_FORMATS["panel"], HUGO, JULIA)
ONE_HOST = Cast.for_format(PODCAST_FORMATS["one_host"], HUGO, None)


def read(text: str, speaker: str = "lead", cast: Cast = PANEL, label: str = "Scott", **kw):
    reader = LineAddress.for_episode(cast, label, speaker, "es", kw.get("is_listening", False))
    return reader.read(text)


# --- tags -----------------------------------------------------------------------------------


@pytest.mark.parametrize("tag", ["[@Julia]", "[@julia]", "[@Julía]", "[@ Julia ]"])
def test_a_tag_naming_the_other_host_is_for_them(tag):
    assert read(f"¿Y tú qué piensas? {tag}") == LineAddressResult(
        "second", "¿Y tú qué piensas?", True
    )


def test_a_tag_naming_the_learner_is_for_the_learner():
    assert read("¿Y tú, comes pan? [@Scott]") == LineAddressResult(
        "learner", "¿Y tú, comes pan?", True
    )


def test_the_all_tag_is_for_no_one_in_particular():
    assert read("Hoy hablamos del café. [@all]") == LineAddressResult(
        None, "Hoy hablamos del café.", True
    )


def test_the_last_of_two_tags_wins_and_both_are_removed():
    result = read("Hola. [@Scott] ¿Y tú? [@Julia]")

    assert (result.addressee, result.text, result.is_from_tag) == ("second", "Hola. ¿Y tú?", True)


def test_an_unnamed_learner_is_tagged_by_their_label():
    assert read("¿Te gusta? [@our guest]", label="our guest").addressee == "learner"


@pytest.mark.parametrize(
    "tag",
    ["[@Marco]", "[@Hugo]", f"[@{'x' * (ADDRESS_TAG_MAX_LENGTH + 1)}]"],
    ids=["nobody", "the-speaker", "too-long"],
)
def test_an_invalid_tag_leaves_the_fallback_to_decide(tag):
    result = read(f"Una idea, Julia. {tag}")

    assert (result.addressee, result.is_from_tag) == ("second", False)


def test_an_invalid_tag_is_still_removed_when_it_fits_the_tag_length():
    assert read("Una idea. [@Marco]").text == "Una idea."


# --- the fallback ---------------------------------------------------------------------------


def test_a_question_naming_participants_is_for_the_last_one_named():
    assert read("Qué buen desayuno, Julia. Scott, ¿los huevos son fritos?").addressee == "learner"


def test_a_question_before_a_closing_quote_counts():
    assert read('Julia dice: "¿por qué?"').addressee == "second"


def test_the_learner_is_named_by_a_guest_label():
    assert read("Bienvenida, invitada. ¿Qué tomas?", label="our guest").addressee == "learner"


def test_a_statement_naming_the_other_host_is_for_them():
    assert read("Hola, Scott. La leche hace el té más suave, Julia.").addressee == "second"


def test_a_statement_naming_only_the_learner_is_for_no_one():
    assert read("Pan con huevos, Scott, es muy bueno.").addressee is None


def test_a_question_naming_no_one_is_for_no_one():
    result = read("¿Por qué el café huele tan bien?")

    assert (result.addressee, result.is_from_tag) == (None, False)


def test_one_host_never_addresses_a_host():
    assert read("¿Y tú, Julia?", cast=ONE_HOST).addressee is None
    assert read("Scott, ¿qué opinas?", cast=ONE_HOST).addressee == "learner"


def test_a_listen_line_is_never_for_the_listeners():
    listening = {"label": "our listeners", "is_listening": True}

    assert read("Scott, ¿qué opinas? [@our listeners]", **listening).addressee is None
    assert read("¿Y tú, Julia? [@Julia]", **listening).addressee == "second"


# --- episode 45 (research R19 rationale), read with no tag ------------------------------------

EPISODE_45 = [
    (
        381,
        "lead",
        "Hola, Scott, bienvenido otra vez. Hoy es el episodio dos, y a ti te encanta el pan, ¿verdad?",
        "learner",
    ),
    (382, "second", "Hola, Hugo. Hola, Scott. Soy Julia, y me gustan los datos.", "lead"),
    (
        384,
        "second",
        "Mucho gusto, Scott. Hoy hablamos de algo pequeño de casa. ¿Te gusta el café o el té?",
        "learner",
    ),
    (
        386,
        "second",
        "Sí, a ti te gusta el café. Hay una duda pequeña: ¿por qué el café huele tan bien por la mañana?",
        None,
    ),
    (387, "lead", "Buena pregunta, Julia. ¿Por qué pasa eso con el café?", "second"),
    (
        388,
        "second",
        'El café tiene muchas cosas pequeñas en el aire. Tu nariz las siente y el cerebro dice: "huele bien".',
        None,
    ),
    (
        389,
        "lead",
        "Qué bien, Julia, el cerebro decide. Scott, ¿el café huele mejor por la mañana o por la noche?",
        "learner",
    ),
    (
        391,
        "second",
        "Scott, te gusta el café por la mañana. La gente toma café para despertar, porque tiene cafeína.",
        None,
    ),
    (
        392,
        "lead",
        "¿Cómo despierta la cafeína el cuerpo, Julia? ¿Y por qué tarda un poco?",
        "second",
    ),
    (
        393,
        "second",
        "La cafeína quita el sueño del cerebro. Tarda un poco, porque llega a la sangre. Scott, ¿tomas café con pan o solo?",
        "learner",
    ),
    (395, "lead", "Café solo, Scott, muy bien. Y el pan, ¿lo comes con otra cosa?", "learner"),
    (
        396,
        "lead",
        "Scott, me gusta tu café solo. ¿Prefieres el pan con mantequilla o sin mantequilla?",
        "learner",
    ),
    (
        398,
        "second",
        "Pan con huevos, Scott, es una comida muy buena. El huevo tiene mucha proteína y da fuerza.",
        None,
    ),
    (
        399,
        "second",
        "Y con el café, Scott, es un desayuno completo. ¿Comes pan con huevos todos los días?",
        "learner",
    ),
    (400, "lead", "Qué buen desayuno, Julia. Scott, ¿los huevos son fritos o cocidos?", "learner"),
    (402, "second", "Me gusta el té con leche, Scott. ¿Tú prefieres el té o el café?", "learner"),
    (403, "lead", "Julia, ¿por qué el té con leche te gusta tanto?", "second"),
    (
        404,
        "second",
        "La leche hace el té más suave, Hugo. Además, el sabor es dulce y calmado.",
        "lead",
    ),
    (
        405,
        "lead",
        "Qué interesante, Julia. Scott, ¿el té con leche es mejor caliente o frío?",
        "learner",
    ),
    (407, "second", "Ah, tu gato llama, Scott. ¿Tiene hambre o quiere jugar?", "learner"),
    (409, "lead", "Ay, Scott, eso suena mal. ¿Tu gato tiene mucho calor?", "learner"),
    (410, "lead", "Gracias por venir, Scott. Adiós, y cuida a tu gato.", None),
]


@pytest.mark.parametrize(
    ("message_id", "speaker", "text", "addressee"), EPISODE_45, ids=lambda v: str(v)[:12]
)
def test_every_episode_45_host_line_finds_its_addressee(message_id, speaker, text, addressee):
    result = read(text, speaker)

    assert (result.addressee, result.text, result.is_from_tag) == (addressee, text, False)


def test_the_episode_45_table_covers_all_22_host_lines():
    assert len(EPISODE_45) == 22
