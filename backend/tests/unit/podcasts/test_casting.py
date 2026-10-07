"""T019: hosts are cast by code, never by the model (research R6, data-model §3)."""

import random
from dataclasses import replace

import pytest

from app.podcasts.catalog import PERSONALITIES, PODCAST_FORMATS, SHOW_TEMPLATES
from app.podcasts.services.casting import Cast, Host, HostCaster, InvalidCast
from app.practice_languages import PRACTICE_LANGUAGES, host_names_for
from app.services.tts.voices import AVAILABLE_VOICES, voices_for
from tests.support.fake_speech import FakeVoiceInstallation

SHOW = SHOW_TEMPLATES["weekend-food-talk"]
GENDER = {voice.key: voice.gender for voice in AVAILABLE_VOICES}


def _caster(installed: set[str] | None = None, seed: int = 0) -> HostCaster:
    return HostCaster(FakeVoiceInstallation(installed), random.Random(seed))


def _keys(language: str) -> list[str]:
    return [voice.key for voice in voices_for(language)]


@pytest.mark.parametrize("language", list(PRACTICE_LANGUAGES))
def test_the_lead_takes_the_first_installed_voice_and_the_second_another(language):
    lead, second = _caster().cast_template(SHOW, language, None)

    assert lead.voice_key == _keys(language)[0]
    assert second.voice_key == _keys(language)[1]


def test_an_uninstalled_voice_is_skipped():
    first, second = _keys("es")

    lead, other = _caster(installed={second}).cast_template(SHOW, "es", None)

    assert lead.voice_key == other.voice_key == second


@pytest.mark.parametrize("language", list(PRACTICE_LANGUAGES))
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


# --- recast: Shuffle on the setup screen (T115, plan interpretation 6) ------------------


def _pair(seed: int = 0, learner_name: str | None = None) -> tuple[Host, Host]:
    return _caster(seed=seed).cast_template(SHOW, "es", learner_name)


@pytest.mark.parametrize("slot", ["lead", "second"])
@pytest.mark.parametrize("seed", range(10))
def test_a_shuffled_host_differs_from_both_hosts_in_name_and_personality(slot, seed):
    hosts = _pair()
    replaced = next(host for host in hosts if host.slot == slot)

    new = _caster(seed=seed).recast(slot, hosts, None)

    assert new.slot == slot
    assert new.name.casefold() not in {host.name.casefold() for host in hosts}
    assert new.personality_id not in {host.personality_id for host in hosts}
    assert new.show_role == replaced.show_role


@pytest.mark.parametrize("seed", range(10))
def test_a_shuffled_host_never_takes_the_learners_name(seed):
    hosts = _pair()
    names = host_names_for("es", GENDER[hosts[1].voice_key])
    learner = next(name for name in names if name not in {h.name for h in hosts})

    new = _caster(seed=seed).recast("second", hosts, learner.lower())

    assert new.name != learner


def test_a_shuffled_hosts_name_suits_its_voice():
    hosts = _pair()

    new = _caster(seed=4).recast("lead", hosts, None)

    assert new.name in host_names_for("es", GENDER[new.voice_key])


def test_a_shuffled_host_keeps_its_voice_when_no_third_voice_is_installed():
    hosts = _pair()

    new = _caster(seed=2).recast("second", hosts, None)

    assert new.voice_key == hosts[1].voice_key


def test_a_host_sharing_the_only_voice_keeps_it():
    only = _keys("es")[0]
    hosts = _caster(installed={only}).cast_template(SHOW, "es", None)

    new = _caster(installed={only}, seed=1).recast("second", hosts, None)

    assert new.voice_key == only


def test_a_host_sharing_a_voice_moves_to_another_installed_one():
    lead, second = _pair()
    shared = (lead, Host("second", second.name, second.personality_id, lead.voice_key, "co_host"))

    new = _caster(seed=1).recast("second", shared, None)

    assert new.voice_key != lead.voice_key


def test_a_third_voice_that_differs_from_the_other_hosts_is_taken(monkeypatch):
    from app.podcasts.services import casting

    voices = voices_for("es")
    third = replace(voices[1], key="es_MX-third-medium")
    monkeypatch.setattr(casting, "voices_for", lambda _language: (*voices, third))
    hosts = _pair()

    new = _caster(seed=0).recast("second", hosts, None)

    assert new.voice_key == third.key


@pytest.mark.parametrize("seed", range(20))
def test_three_shuffles_in_a_row_never_clash(seed):
    caster = _caster(seed=seed)
    hosts = _pair()
    for slot in ("second", "lead", "second"):
        new = caster.recast(slot, hosts, "Sam")
        hosts = tuple(new if host.slot == slot else host for host in hosts)

        Cast(*hosts)
        assert hosts[0].voice_key != hosts[1].voice_key
        assert "sam" not in {host.name.casefold() for host in hosts}
