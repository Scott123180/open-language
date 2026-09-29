"""Builders for podcast storage inputs, so each test states only what it cares about."""

from dataclasses import replace

from app.podcasts.services.storage import NewEpisode, NewHost

VOICE_BY_SLOT = {"lead": "es_AR-daniela-high", "second": "es_ES-davefx-medium"}
ROLE_BY_SLOT = {"lead": "host", "second": "co_host"}


def new_host(slot: str, name: str, personality_id: str = "enthusiast") -> NewHost:
    return NewHost(
        slot=slot,
        name=name,
        personality_id=personality_id,
        voice_key=VOICE_BY_SLOT[slot],
        show_role=ROLE_BY_SLOT[slot],
    )


DEFAULT_EPISODE = NewEpisode(
    show_source="ready_made",
    show_id="weekend-food-talk",
    title="Weekend Food Talk",
    premise="Two food lovers swap weekend cooking wins and disasters.",
    topic="food",
    learner_role="guest",
    format="panel",
    length="short",
    learner_name=None,
    target_language="es",
    native_language="en",
    llm_model="test-model",
    hosts=(new_host("lead", "Lucía"), new_host("second", "Marco", "dry_sceptic")),
)


def new_episode(**overrides) -> NewEpisode:
    return replace(DEFAULT_EPISODE, **overrides)
