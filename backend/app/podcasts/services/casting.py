"""Who the hosts are: names, personalities and voices, cast by code (research R6).

The model never names a host. A name comes from the language's name bank for the gender of the
host's voice, a voice from the installed voices for the language, and a personality from the
catalogue. Two hosts never share a name or a personality, and share a voice only when the
language has one installed voice (FR-007).
"""

import hashlib
import random
from dataclasses import dataclass

from app.podcasts.catalog import (
    HOST_NAME_MAX_LENGTH,
    LEAD_SLOT,
    PERSONALITIES,
    SECOND_SLOT,
    PodcastFormat,
    ShowTemplate,
)
from app.practice_languages import host_names_for
from app.services.tts.base import VoiceInstallation
from app.services.tts.voices import AVAILABLE_VOICES, VoiceInfo, voices_for

SHOW_ROLE_BY_SLOT = {LEAD_SLOT: "host", SECOND_SLOT: "co_host"}
_VOICES = {voice.key: voice for voice in AVAILABLE_VOICES}


class InvalidCast(ValueError):  # noqa: N818 — reads as the invariant it guards
    """A host or pair of hosts that data-model §3 does not allow."""


@dataclass(frozen=True, slots=True)
class Host:
    slot: str
    name: str
    personality_id: str
    voice_key: str
    show_role: str
    angle: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip() or len(self.name) > HOST_NAME_MAX_LENGTH:
            raise InvalidCast(f"A host's name is 1–{HOST_NAME_MAX_LENGTH} characters.")
        if self.personality_id not in PERSONALITIES:
            raise InvalidCast(f"{self.personality_id!r} is not a catalogued personality.")


@dataclass(frozen=True, slots=True)
class Cast:
    """The hosts who take part in an episode. One host has no second host."""

    lead: Host
    second: Host | None

    def __post_init__(self) -> None:
        if self.second is None:
            return
        if self.lead.name.casefold() == self.second.name.casefold():
            raise InvalidCast("The two hosts need different names.")
        if self.lead.personality_id == self.second.personality_id:
            raise InvalidCast("The two hosts need different personalities.")

    @classmethod
    def for_format(cls, podcast_format: PodcastFormat, lead: Host, second: Host | None) -> "Cast":
        if (second is not None) != (podcast_format.host_count == 2):
            raise InvalidCast(f"{podcast_format.label} has {podcast_format.host_count} host(s).")
        return cls(lead, second)

    @property
    def hosts(self) -> tuple[Host, ...]:
        return (self.lead,) if self.second is None else (self.lead, self.second)

    def host(self, slot: str) -> Host:
        return next(host for host in self.hosts if host.slot == slot)


class HostCaster:
    def __init__(self, installation: VoiceInstallation, rng: random.Random) -> None:
        self._installation = installation
        self._rng = rng

    def cast_template(
        self, template: ShowTemplate, language: str, learner_name: str | None
    ) -> tuple[Host, Host]:
        """A ready-made show's hosts, with names that are stable for the show and language."""
        voices = self.voices_for(language)
        taken = _names_taken(learner_name)
        lead_name = _stable_name(template.show_id, LEAD_SLOT, voices[0], language, taken)
        second_name = _stable_name(
            template.show_id, SECOND_SLOT, voices[1], language, taken | {lead_name.casefold()}
        )
        lead_personality, second_personality = template.default_personalities
        return (
            _host(LEAD_SLOT, lead_name, lead_personality, voices[0], None),
            _host(SECOND_SLOT, second_name, second_personality, voices[1], None),
        )

    def cast_personalities(
        self,
        personalities: tuple[str, str],
        language: str,
        learner_name: str | None,
        angles: tuple[str | None, str | None] = (None, None),
    ) -> tuple[Host, Host]:
        """Hosts for a generated show: random names that suit the language and voices."""
        voices = self.voices_for(language)
        taken = _names_taken(learner_name)
        lead_name = self._random_name(voices[0], language, taken)
        second_name = self._random_name(voices[1], language, taken | {lead_name.casefold()})
        return (
            _host(LEAD_SLOT, lead_name, personalities[0], voices[0], angles[0]),
            _host(SECOND_SLOT, second_name, personalities[1], voices[1], angles[1]),
        )

    def recast(self, slot: str, hosts: tuple[Host, Host], learner_name: str | None) -> Host:
        """Shuffle: a new host for `slot`, unlike either host in name and personality.

        The voice stays unless a third installed voice differs from the other host's, or the
        two hosts share a voice and another is installed (plan interpretation 6)."""
        replaced = next(host for host in hosts if host.slot == slot)
        other = next(host for host in hosts if host.slot != slot)
        voice = self._recast_voice(replaced, other)
        taken = _names_taken(learner_name) | {replaced.name.casefold(), other.name.casefold()}
        name = self._random_name(voice, voice.language, taken)
        used = {replaced.personality_id, other.personality_id}
        personality = self._rng.choice([key for key in PERSONALITIES if key not in used])
        return _host(slot, name, personality, voice, None)

    def _recast_voice(self, replaced: Host, other: Host) -> VoiceInfo:
        catalogue = voices_for(_VOICES[replaced.voice_key].language)
        fresh = [
            voice
            for voice in catalogue
            if voice.key not in {replaced.voice_key, other.voice_key}
            and self._installation.is_installed(voice.key)
        ]
        return self._rng.choice(fresh) if fresh else _VOICES[replaced.voice_key]

    def voices_for(self, language: str) -> tuple[VoiceInfo, VoiceInfo]:
        """The lead's voice and the second host's: installed voices first, never another
        language's. With one installed voice both share it; with none, the catalogue's."""
        catalogue = voices_for(language)
        installed = [v for v in catalogue if self._installation.is_installed(v.key)]
        usable = installed or list(catalogue)
        return usable[0], usable[1] if len(usable) > 1 else usable[0]

    def _random_name(self, voice: VoiceInfo, language: str, taken: set[str]) -> str:
        return self._rng.choice(_free_names(voice, language, taken))


def _host(slot: str, name: str, personality: str, voice: VoiceInfo, angle: str | None) -> Host:
    return Host(slot, name, personality, voice.key, SHOW_ROLE_BY_SLOT[slot], angle)


def _names_taken(learner_name: str | None) -> set[str]:
    return {learner_name.strip().casefold()} if learner_name and learner_name.strip() else set()


def _free_names(voice: VoiceInfo, language: str, taken: set[str]) -> list[str]:
    return [name for name in host_names_for(language, voice.gender) if name.casefold() not in taken]


def _stable_name(show_id: str, slot: str, voice: VoiceInfo, language: str, taken: set[str]) -> str:
    """The same show, slot and language always open with the same name, unless it is taken."""
    names = host_names_for(language, voice.gender)
    digest = hashlib.sha256(f"{show_id}:{slot}".encode()).hexdigest()
    start = int(digest, 16) % len(names)
    ordered = names[start:] + names[:start]
    return next(name for name in ordered if name.casefold() not in taken)
