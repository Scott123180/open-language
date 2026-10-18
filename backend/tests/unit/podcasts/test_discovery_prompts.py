"""010 T121: the Find a new show prompt and schema (contracts §9)."""

from app.podcasts.catalog import SUGGESTION_SEEDS
from app.podcasts.prompts import DISCOVERY_JSON_SCHEMA, SHOW_JSON_SCHEMA, discovery_prompt
from app.podcasts.services.surprise import SurpriseIdea
from app.practice_languages import ConversationLanguages

SEEDS = (SurpriseIdea("chess", "a quiz show about"), SurpriseIdea("night trains", "the history of"))
PROMPT = discovery_prompt(SEEDS, ("Board Game Night",), ConversationLanguages.of("es", "en"))


def test_the_schema_is_a_list_of_up_to_five_generator_shows():
    shows = DISCOVERY_JSON_SCHEMA["properties"]["shows"]

    assert DISCOVERY_JSON_SCHEMA["required"] == ["shows"]
    assert (shows["minItems"], shows["maxItems"]) == (1, SUGGESTION_SEEDS)
    assert shows["items"] == SHOW_JSON_SCHEMA


def test_the_prompt_lists_every_seed_and_every_title_to_avoid():
    assert "a quiz show about chess" in PROMPT and "the history of night trains" in PROMPT
    assert '"Board Game Night"' in PROMPT


def test_the_prompt_reuses_the_generators_rules():
    assert "is_suitable to false" in PROMPT
    assert "a short, catchy show title" in PROMPT
    assert "curious_interviewer" in PROMPT


def test_the_prompt_names_languages_not_codes():
    assert "Spanish" in PROMPT and "English" in PROMPT
    assert " es " not in PROMPT and "(es)" not in PROMPT
