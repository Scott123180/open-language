"""010 T119: Find a new show: seeds, one structured call, filtering and the top-up (R10)."""

import random

import pytest

from app.podcasts.catalog import (
    INTEREST_SEEDS,
    MIN_SUGGESTIONS,
    SHOW_TEMPLATES,
    SUGGESTION_SEEDS,
)
from app.podcasts.services.casting import HostCaster
from app.podcasts.services.discovery import (
    NotEnoughSuggestions,
    ShowDiscovery,
    SuggestionContext,
    SuggestionSeeds,
    normalise_title,
)
from app.podcasts.services.surprise import SURPRISE_TOPICS
from app.practice_languages import ConversationLanguages
from app.services.llm.base import LLMError
from tests.support.fake_speech import FakeVoiceInstallation
from tests.support.scripted_memory_llm import ScriptedMemoryLLM
from tests.support.scripted_show_llm import SUITABLE_SHOW

SPANISH = ConversationLanguages.of("es", "en")


def _show(title: str, **changes) -> dict:
    return {**SUITABLE_SHOW, "title": title, **changes}


def _context(**changes) -> SuggestionContext:
    values = {
        "avoid_titles": (),
        "interests": (),
        "mine_titles": (),
        "languages": SPANISH,
        "learner_name": None,
    }
    return SuggestionContext(**{**values, **changes})


@pytest.fixture
def llm() -> ScriptedMemoryLLM:
    return ScriptedMemoryLLM()


@pytest.fixture
def discovery(llm) -> ShowDiscovery:
    caster = HostCaster(FakeVoiceInstallation(), random.Random(3))
    return ShowDiscovery(llm, caster, SuggestionSeeds(random.Random(5)))


# --- seeds ---------------------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(20))
def test_with_interests_exactly_the_quota_of_seeds_come_from_them(seed):
    interests = ("chess", "jazz")

    seeds = SuggestionSeeds(random.Random(seed)).draw(interests)

    assert len(seeds) == SUGGESTION_SEEDS == len(set(seeds))
    assert sum(seed.topic in interests for seed in seeds) == INTEREST_SEEDS


@pytest.mark.parametrize("seed", range(20))
def test_without_interests_every_seed_is_a_built_in_topic(seed):
    seeds = SuggestionSeeds(random.Random(seed)).draw(())

    assert len(set(seeds)) == SUGGESTION_SEEDS
    assert all(seed.topic in SURPRISE_TOPICS for seed in seeds)


def test_a_title_is_compared_without_case_punctuation_or_spacing():
    assert normalise_title("  Night  Trains, of Europe! ") == normalise_title(
        "night trains of europe"
    )


# --- one call, filtered ----------------------------------------------------------------------


def test_one_call_returns_suggested_shows_with_hosts_cast_by_code(discovery, llm):
    llm.queue({"shows": [_show(f"Show {n}") for n in range(5)]})

    shows = discovery.suggest(_context())

    assert len(llm.calls) == 1
    assert [show.title for show in shows] == [f"Show {n}" for n in range(5)]
    assert all(host.name != "Florence" for show in shows for host in show.hosts)


def test_unsuitable_unreadable_and_duplicate_shows_are_dropped(discovery, llm):
    template_title = next(iter(SHOW_TEMPLATES.values())).title
    llm.queue(
        {
            "shows": [
                _show("Keep One"),
                _show("Bad", is_suitable=False),
                _show("Broken", hosts=[]),
                _show(template_title.upper() + "!"),
                _show("Mine Already"),
                _show("Seen Before"),
                _show("keep one"),
                _show("Keep Two"),
                _show("Keep Three"),
            ]
        }
    )

    shows = discovery.suggest(
        _context(avoid_titles=("seen before",), mine_titles=("Mine already",))
    )

    assert [show.title for show in shows] == ["Keep One", "Keep Two", "Keep Three"]
    assert len(llm.calls) == 1


def test_too_few_survivors_get_one_top_up_call_with_fresh_seeds(discovery, llm):
    llm.queue({"shows": [_show("One"), _show("Two")]}, {"shows": [_show("Three"), _show("Two")]})

    shows = discovery.suggest(_context())

    assert [show.title for show in shows] == ["One", "Two", "Three"]
    assert len(llm.calls) == 2
    assert llm.prompts[0] != llm.prompts[1]


def test_still_too_few_after_the_top_up_is_refused(discovery, llm):
    llm.queue({"shows": [_show("One")]}, {"shows": [_show("Two")]})

    with pytest.raises(NotEnoughSuggestions):
        discovery.suggest(_context())

    assert MIN_SUGGESTIONS == 3


def test_an_unreadable_reply_counts_as_no_shows(discovery, llm):
    llm.queue("not json", {"shows": [_show("One"), _show("Two"), _show("Three")]})

    assert len(discovery.suggest(_context())) == 3


def test_a_provider_error_is_raised_unchanged(discovery, llm):
    error = LLMError("down", "Ollama isn't running.")
    llm.queue(error)

    with pytest.raises(LLMError) as raised:
        discovery.suggest(_context())

    assert raised.value is error
