"""T019: hosts are cast by code, never by the model (research R6, data-model §3)."""

import random

import pytest

from app.podcasts.catalog import PERSONALITIES, PODCAST_FORMATS, SHOW_TEMPLATES
from app.podcasts.services.casting import Cast, Host, HostCaster, InvalidCast
from app.practice_languages import host_names_for
from app.services.tts.voices import AVAILABLE_VOICES, voices_for
from tests.support.fake_speech import FakeVoiceInstallation

SHOW = SHOW_TEMPLATES["weekend-food-talk"]
GENDER = {voice.key: voice.gender for voice in AVAILABLE_VOICES}


def _caster(installed: set[str] | None = None, seed: int = 0) -> HostCaster:
    return HostCaster(FakeVoiceInstallation(installed), random.Random(seed))


def _keys(language: str) -> list[str]:
    return [voice.key for voice in voices_for(language)]


@pytest.mark.parametrize("language", ["es", "de"])
def test_the_lead_takes_the_first_installed_voice_and_the_second_another(language):
    lead, second = _caster().cast_template(SHOW, language, None)

    assert lead.voice_key == _keys(language)[0]
    assert second.voice_key == _keys(language)[1]


def test_an_uninstalled_voice_is_skipped():
    first, second = _keys("es")

    lead, other = _caster(installed={second}).cast_template(SHOW, "es", None)

    assert lead.voice_key == other.voice_key == second


@pytest.mark.parametrize("language", ["es", "de"])
@pytest.mark.parametrize("show_id", list(SHOW_TEMPLATES))
def test_names_suit_the_language_and_the_voice(language, show_id):
    for host in _caster().cast_template(SHOW_TEMPLATES[show_id], language, None):
        assert host.name in host_names_for(language, GENDER[host.voice_key])


@pytest.mark.parametrize("show_id", list(SHOW_TEMPLATES))
def test_the_hosts_differ_in_name_and_personality(show_id):
    lead, second = _caster().cast_template(SHOW_TEMPLATES[show_id], "es", None)

    assert lead.name.casefold() != second.name.casefold()
    assert lead.personality_id != second.personality_id


@pytest.mark.parametrize("show_id", list(SHOW_TEMPLATES))
def test_the_show_keeps_its_default_personalities(show_id):
    show = SHOW_TEMPLATES[show_id]

    lead, second = _caster().cast_template(show, "es", None)

    assert (lead.personality_id, second.personality_id) == show.default_personalities


@pytest.mark.parametrize("show_id", list(SHOW_TEMPLATES))
def test_a_ready_made_shows_names_are_stable(show_id):
    show = SHOW_TEMPLATES[show_id]

    first = _caster(seed=1).cast_template(show, "de", None)
    again = _caster(seed=2).cast_template(show, "de", None)

    assert [h.name for h in first] == [h.name for h in again]


@pytest.mark.parametrize("show_id", list(SHOW_TEMPLATES))
def test_no_host_is_named_like_the_learner(show_id):
    show = SHOW_TEMPLATES[show_id]
    default_lead, _ = _caster().cast_template(show, "es", None)

    lead, second = _caster().cast_template(show, "es", default_lead.name.upper())

    assert default_lead.name.casefold() not in {lead.name.casefold(), second.name.casefold()}


def test_with_one_voice_both_hosts_share_it_and_still_differ_in_name():
    only = _keys("es")[0]

    lead, second = _caster(installed={only}).cast_template(SHOW, "es", None)

    assert lead.voice_key == second.voice_key == only
    assert lead.name != second.name


def test_with_no_voice_installed_the_hosts_are_still_cast():
    lead, second = _caster(installed=set()).cast_template(SHOW, "es", None)

    assert {lead.voice_key, second.voice_key} <= set(_keys("es"))
    assert lead.name and second.name


def test_the_roles_are_host_and_co_host():
    lead, second = _caster().cast_template(SHOW, "es", None)

    assert (lead.slot, lead.show_role, second.slot, second.show_role) == (
        "lead",
        "host",
        "second",
        "co_host",
    )


def test_personalities_can_be_cast_with_random_names_and_angles():
    lead, second = _caster(seed=3).cast_personalities(
        ("joker", "expert"), "es", "Sam", ("Knows every stadium", None)
    )

    assert (lead.personality_id, second.personality_id) == ("joker", "expert")
    assert (lead.angle, second.angle) == ("Knows every stadium", None)
    assert lead.name != second.name


# --- Cast invariants --------------------------------------------------------------------

LUCIA = Host("lead", "Lucía", "enthusiast", "es_AR-daniela-high", "host")
MARCO = Host("second", "Marco", "dry_sceptic", "es_ES-davefx-medium", "co_host")


def test_one_host_takes_no_second_host():
    with pytest.raises(InvalidCast):
        Cast.for_format(PODCAST_FORMATS["one_host"], LUCIA, MARCO)


def test_two_hosts_need_a_second_host():
    with pytest.raises(InvalidCast):
        Cast.for_format(PODCAST_FORMATS["panel"], LUCIA, None)


def test_two_hosts_cannot_share_a_name():
    twin = Host("second", "lucía", "joker", "es_ES-davefx-medium", "co_host")

    with pytest.raises(InvalidCast):
        Cast.for_format(PODCAST_FORMATS["panel"], LUCIA, twin)


def test_two_hosts_cannot_share_a_personality():
    same = Host("second", "Marco", "enthusiast", "es_ES-davefx-medium", "co_host")

    with pytest.raises(InvalidCast):
        Cast.for_format(PODCAST_FORMATS["panel"], LUCIA, same)


@pytest.mark.parametrize("name", ["", "   ", "x" * 41])
def test_a_host_name_is_one_to_forty_characters(name):
    with pytest.raises(InvalidCast):
        Host("lead", name, "enthusiast", "es_AR-daniela-high", "host")


def test_a_host_has_a_catalogued_personality():
    with pytest.raises(InvalidCast):
        Host("lead", "Lucía", "grumpy", "es_AR-daniela-high", "host")


def test_the_cast_lists_its_hosts_in_slot_order():
    cast = Cast.for_format(PODCAST_FORMATS["panel"], LUCIA, MARCO)

    assert cast.hosts == (LUCIA, MARCO)
    assert cast.host("second") is MARCO
    assert set(PERSONALITIES) >= {h.personality_id for h in cast.hosts}
