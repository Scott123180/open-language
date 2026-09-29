"""Request and response shapes of /api/podcasts (contracts §1–§8), and draft validation.

A show draft comes back from the client, so it is checked again before an episode starts
(data-model §6). Every refusal is a plain sentence that names the host and the field.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.podcasts.catalog import (
    EPISODE_LENGTHS,
    HOST_NAME_MAX_LENGTH,
    HOST_SLOTS,
    LEARNER_ROLES,
    PERSONALITIES,
    PODCAST_FORMATS,
    SHOW_ROLES,
    SHOW_SOURCES,
    TITLE_MAX_LENGTH,
)
from app.practice_languages import language_name
from app.services.tts.voices import AVAILABLE_VOICES

LANGUAGE_CHANGED = "The practice language changed. Pick the show again."
MAX_INTERESTS = 10
INTEREST_MAX_LENGTH = 40
FORMAT_PATTERN = f"^({'|'.join(PODCAST_FORMATS)})$"
LENGTH_PATTERN = f"^({'|'.join(EPISODE_LENGTHS)})$"
SLOT_PATTERN = f"^({'|'.join(HOST_SLOTS)})$"
SOURCE_PATTERN = f"^({'|'.join(SHOW_SOURCES)})$"
_VOICE_LANGUAGES = {voice.key: voice.language for voice in AVAILABLE_VOICES}


def _trimmed_name(value: str | None) -> str | None:
    """A learner name, trimmed; blank means none. Over the limit raises a 422."""
    if value is None or not value.strip():
        return None
    trimmed = value.strip()
    if len(trimmed) > HOST_NAME_MAX_LENGTH:
        raise ValueError(f"Your name can be at most {HOST_NAME_MAX_LENGTH} characters.")
    return trimmed


def _clean_interests(values: list[str]) -> list[str]:
    """Trimmed, blanks dropped, de-duplicated ignoring case (first spelling kept) (contracts §2)."""
    cleaned: dict[str, str] = {}
    for value in (value.strip() for value in values):
        if len(value) > INTEREST_MAX_LENGTH:
            raise ValueError(
                f"“{value}” is too long: an interest can be at most {INTEREST_MAX_LENGTH} characters."
            )
        if value:
            cleaned.setdefault(value.casefold(), value)
    if len(cleaned) > MAX_INTERESTS:
        raise ValueError(f"You can save at most {MAX_INTERESTS} interests.")
    return list(cleaned.values())


# --- catalogue ----------------------------------------------------------------------------


class FormatOption(BaseModel):
    format_id: str
    label: str
    host_count: int
    is_learner_speaking: bool
    description: str


class LengthOption(BaseModel):
    length_id: str
    label: str
    target_host_lines: int
    is_default: bool


class PersonalityOption(BaseModel):
    personality_id: str
    label: str
    description: str


class HostDraftModel(BaseModel):
    slot: str = Field(pattern=SLOT_PATTERN)
    name: str = Field(min_length=1, max_length=HOST_NAME_MAX_LENGTH)
    personality_id: str
    voice_key: str
    show_role: str
    angle: str | None = None


class ShowDraftModel(BaseModel):
    source: str = Field(pattern=SOURCE_PATTERN)
    show_id: str | None = None
    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    premise: str = Field(min_length=1)
    topic: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    learner_role: str
    language: str
    hosts: list[HostDraftModel] = Field(min_length=2, max_length=2)


class CatalogVoices(BaseModel):
    installed_count: int
    shared_voice_notice: str | None
    unavailable_message: str | None


class CatalogResponse(BaseModel):
    language: str
    language_name: str
    formats: list[FormatOption]
    lengths: list[LengthOption]
    personalities: list[PersonalityOption]
    shows: list[ShowDraftModel]
    voices: CatalogVoices


# --- preferences --------------------------------------------------------------------------


class PreferencesResponse(BaseModel):
    last_format: str
    is_show_text_on: bool
    interests: list[str]
    learner_name: str | None


class UpdatePreferencesRequest(BaseModel):
    """Any subset of the writable preferences. `last_format` is read-only (contracts §2)."""

    is_show_text_on: bool | None = None
    interests: list[str] | None = None
    learner_name: str | None = None

    @field_validator("learner_name")
    @classmethod
    def _trim_learner_name(cls, value: str | None) -> str | None:
        return _trimmed_name(value)

    @field_validator("interests")
    @classmethod
    def _clean_interests(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _clean_interests(value)


# --- shows (contracts §3) -----------------------------------------------------------------


class GenerateShowRequest(BaseModel):
    """The idea is checked in the router, so a blank or long one gets the plain message."""

    idea: str
    avoid_titles: list[str] = Field(default_factory=list)


class ShowRefusal(BaseModel):
    detail: str
    can_surprise: bool


# --- episodes -----------------------------------------------------------------------------


class StartEpisodeRequest(BaseModel):
    show: ShowDraftModel
    format: str = Field(pattern=FORMAT_PATTERN)
    length: str = Field(pattern=LENGTH_PATTERN)
    learner_name: str | None = None

    @field_validator("learner_name")
    @classmethod
    def _trim_learner_name(cls, value: str | None) -> str | None:
        return _trimmed_name(value)


class EpisodeShowModel(BaseModel):
    title: str
    premise: str
    topic: str
    learner_role: str
    source: str
    show_id: str | None


class EpisodeHostModel(BaseModel):
    host_id: int
    slot: str
    name: str
    personality_id: str
    personality_label: str
    voice_key: str
    show_role: str
    is_voice_available: bool
    voice_unavailable_message: str | None


class EpisodeLineModel(BaseModel):
    message_id: int
    speaker: str
    host_id: int | None
    content: str
    intent: str | None
    invites_learner: bool
    is_revealed: bool
    created_at: datetime


class EpisodeResponse(BaseModel):
    conversation_id: int
    status: str
    language: str
    language_name: str
    native_language_name: str
    show: EpisodeShowModel
    format: str
    format_label: str
    length: str
    target_host_lines: int
    learner_name: str | None
    hosts: list[EpisodeHostModel]
    shared_voice_notice: str | None
    turn: str
    awaiting: str | None
    can_jump_in: bool
    can_pass: bool
    lines: list[EpisodeLineModel]


class EpisodeSummaryRow(BaseModel):
    conversation_id: int
    show_title: str
    format: str
    format_label: str
    host_names: list[str]
    language: str
    language_name: str
    status: str


# --- draft validation (data-model §6) -----------------------------------------------------


def validate_draft(
    draft: ShowDraftModel, language: str, learner_name: str | None, installed_count: int
) -> str | None:
    """The first reason the draft cannot start an episode, or None when it can."""
    if draft.language != language:
        return LANGUAGE_CHANGED
    if draft.learner_role not in LEARNER_ROLES:
        return "The show's learner role must be guest, co_host or caller."
    if sorted(host.slot for host in draft.hosts) != sorted(HOST_SLOTS):
        return "A show needs a lead host and a second host."
    for host in draft.hosts:
        problem = _host_problem(host, language, learner_name)
        if problem is not None:
            return problem
    return _pair_problem(*draft.hosts, installed_count=installed_count)


def _host_problem(host: HostDraftModel, language: str, learner_name: str | None) -> str | None:
    if host.personality_id not in PERSONALITIES:
        return f"{host.name}: that personality isn't in the list. Pick one of the listed ones."
    if _VOICE_LANGUAGES.get(host.voice_key) != language:
        return f"{host.name}: that voice doesn't speak {language_name(language)}."
    if host.show_role not in SHOW_ROLES:
        return f"{host.name}: the show role must be host, co_host or guest_expert."
    if learner_name and host.name.casefold() == learner_name.casefold():
        return f"{host.name} has the same name as you. Shuffle the host or change your name."
    return None


def _pair_problem(lead: HostDraftModel, second: HostDraftModel, installed_count: int) -> str | None:
    if lead.name.strip().casefold() == second.name.strip().casefold():
        return f"{lead.name} and {second.name}: the two hosts need different names."
    if lead.personality_id == second.personality_id:
        return f"{lead.name} and {second.name}: the two hosts need different personalities."
    if installed_count >= 2 and lead.voice_key == second.voice_key:
        return f"{lead.name} and {second.name}: the two hosts need different voices."
    return None
