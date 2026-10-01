"""T103: a generated show comes from one structured call; code casts the hosts (research R9)."""

import json
import logging
import random

import pytest

from app.podcasts.catalog import PERSONALITIES
from app.podcasts.services.casting import HostCaster
from app.podcasts.services.generator import (
    ShowDeclined,
    ShowGenerator,
    ShowIdea,
    UnreadableShowError,
)
from app.practice_languages import ConversationLanguages, host_names_for
from app.services.llm.base import LLMError
from app.services.tts.voices import AVAILABLE_VOICES
from tests.support.fake_speech import FakeVoiceInstallation
from tests.support.scripted_show_llm import DECLINED_SHOW, SUITABLE_SHOW, ScriptedShowLLM

GENDER = {voice.key: voice.gender for voice in AVAILABLE_VOICES}
SPANISH = ConversationLanguages.of("es", "en")


def _generator(llm: ScriptedShowLLM) -> ShowGenerator:
    return ShowGenerator(llm, HostCaster(FakeVoiceInstallation(None), random.Random(3)))


def _idea(**overrides) -> ShowIdea:
    return ShowIdea(**{"idea": "living abroad as a nurse", "languages": SPANISH, **overrides})


def _with_hosts(*personalities: str) -> dict:
    hosts = [{"name": "X", "personality": p, "angle": "An angle."} for p in personalities]
    return {**SUITABLE_SHOW, "hosts": hosts}


def test_a_suitable_reply_becomes_a_show_with_the_models_text():
    show = _generator(ScriptedShowLLM()).generate(_idea())

    assert show.title == SUITABLE_SHOW["title"]
    assert show.premise == SUITABLE_SHOW["premise"]
    assert show.topic == SUITABLE_SHOW["topic"]
    assert show.learner_role == "caller"


def test_each_host_keeps_the_models_personality_and_angle():
    lead, second = _generator(ScriptedShowLLM()).generate(_idea()).hosts

    assert (lead.personality_id, lead.angle) == ("storyteller", "Misses her home town.")
    assert (second.personality_id, second.angle) == (
        "dry_sceptic",
        "Thinks the pay is not worth it.",
    )


def test_names_and_voices_are_cast_by_code_whatever_the_model_wrote():
    hosts = _generator(ScriptedShowLLM()).generate(_idea()).hosts

    for host in hosts:
        assert host.name not in ("Florence", "Mary")
        assert host.name in host_names_for("es", GENDER[host.voice_key])
    assert hosts[0].name != hosts[1].name


def test_no_host_takes_the_learners_name():
    for seed in range(20):
        caster = HostCaster(FakeVoiceInstallation(None), random.Random(seed))
        generator = ShowGenerator(ScriptedShowLLM(), caster)
        taken = host_names_for("es", GENDER[caster.voices_for("es")[0].key])[0]

        hosts = generator.generate(_idea(learner_name=taken)).hosts

        assert taken not in [host.name for host in hosts]


def test_a_duplicate_personality_is_replaced_by_the_catalogues_next_one():
    llm = ScriptedShowLLM(_with_hosts("joker", "joker"))

    lead, second = _generator(llm).generate(_idea()).hosts

    order = list(PERSONALITIES)
    assert lead.personality_id == "joker"
    assert second.personality_id == order[(order.index("joker") + 1) % len(order)]


def test_the_last_personality_wraps_to_the_first():
    last = list(PERSONALITIES)[-1]
    llm = ScriptedShowLLM(_with_hosts(last, last))

    _lead, second = _generator(llm).generate(_idea()).hosts

    assert second.personality_id == list(PERSONALITIES)[0]


def test_a_blank_angle_becomes_none():
    reply = {**SUITABLE_SHOW, "hosts": [{**host, "angle": " "} for host in SUITABLE_SHOW["hosts"]]}

    hosts = _generator(ScriptedShowLLM(reply)).generate(_idea()).hosts

    assert [host.angle for host in hosts] == [None, None]


def test_the_prompt_carries_the_idea_and_names_the_languages():
    llm = ScriptedShowLLM()

    _generator(llm).generate(_idea())

    assert "living abroad as a nurse" in llm.last_prompt
    assert "Spanish" in llm.last_prompt
    assert "English" in llm.last_prompt


def test_the_prompt_carries_the_interests_when_there_are_some():
    llm = ScriptedShowLLM()

    _generator(llm).generate(_idea(interests=("football", "cooking")))

    assert "football" in llm.last_prompt
    assert "cooking" in llm.last_prompt


def test_the_prompt_has_no_interests_line_without_interests():
    llm = ScriptedShowLLM()

    _generator(llm).generate(_idea())

    assert "interest" not in llm.last_prompt.lower()


def test_the_prompt_lists_every_title_to_avoid():
    llm = ScriptedShowLLM()

    _generator(llm).generate(_idea(avoid_titles=("Tiki-Taka Talk", "Nurses Abroad")))

    assert "Tiki-Taka Talk" in llm.last_prompt
    assert "Nurses Abroad" in llm.last_prompt


def test_the_schema_limits_personalities_and_roles_to_the_catalogues():
    llm = ScriptedShowLLM()

    _generator(llm).generate(_idea())

    schema = json.dumps(llm.schemas[-1])
    assert all(personality in schema for personality in PERSONALITIES)
    assert "co_host" in schema


def test_an_unsuitable_idea_is_declined_without_the_models_reason(caplog):
    llm = ScriptedShowLLM(DECLINED_SHOW)

    with caplog.at_level(logging.INFO), pytest.raises(ShowDeclined) as declined:
        _generator(llm).generate(_idea())

    assert DECLINED_SHOW["decline_reason"] not in str(declined.value)
    assert DECLINED_SHOW["decline_reason"] in caplog.text


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "[]",
        json.dumps({**SUITABLE_SHOW, "learner_role": "villain"}),
        json.dumps(_with_hosts("enthusiast", "astronaut")),
        json.dumps(_with_hosts("enthusiast")),
        json.dumps({**SUITABLE_SHOW, "title": "  "}),
        json.dumps({key: value for key, value in SUITABLE_SHOW.items() if key != "premise"}),
    ],
)
def test_an_unreadable_reply_is_a_provider_error_with_a_plain_retry(raw):
    llm = ScriptedShowLLM()
    llm.raw_reply = raw

    with pytest.raises(UnreadableShowError) as unreadable:
        _generator(llm).generate(_idea())

    assert isinstance(unreadable.value, LLMError)
    assert "try again" in unreadable.value.user_message.lower()
