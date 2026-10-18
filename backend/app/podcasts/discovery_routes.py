"""/api/podcasts/shows/discover: Find a new show (010 contracts §4).

Suggestions are drafts, like a generated show's, and nothing is stored until the learner
favourites one or plays an episode of it (FR-019). A provider failure is the provider's own
503; too few suitable shows is a plain 503 (FR-020).
"""

import random

from fastapi import APIRouter, Depends, HTTPException

from app.podcasts.responses import show_draft
from app.podcasts.schemas import DiscoverRequest, DiscoverResponse
from app.podcasts.series_routes import get_show_library
from app.podcasts.services.casting import HostCaster
from app.podcasts.services.discovery import (
    NotEnoughSuggestions,
    ShowDiscovery,
    SuggestionContext,
    SuggestionSeeds,
)
from app.podcasts.services.library import ShowLibrary
from app.podcasts.services.storage import PodcastStorage
from app.practice_languages import ConversationLanguages
from app.services.factory import (
    get_app_settings,
    get_host_caster,
    get_podcast_storage,
    get_structured_llm,
)
from app.services.llm.base import StructuredLLMProvider
from app.services.storage.base import AppSettingsRecord

discovery_router = APIRouter(tags=["podcasts"])

NOT_ENOUGH = "Find a new show didn't come up with enough shows this time. Please try again."
SUGGESTED_SOURCE = "suggested"
UNAVAILABLE_STATUS = 503


def get_suggestion_seeds() -> SuggestionSeeds:
    """Fresh randomness per request; tests inject a seeded one."""
    return SuggestionSeeds(random.Random())


def get_show_discovery(
    structured_llm: StructuredLLMProvider = Depends(get_structured_llm),
    caster: HostCaster = Depends(get_host_caster),
    seeds: SuggestionSeeds = Depends(get_suggestion_seeds),
) -> ShowDiscovery:
    return ShowDiscovery(structured_llm, caster, seeds)


def _context(
    req: DiscoverRequest,
    app_settings: AppSettingsRecord = Depends(get_app_settings),
    podcasts: PodcastStorage = Depends(get_podcast_storage),
    library: ShowLibrary = Depends(get_show_library),
) -> SuggestionContext:
    preferences = podcasts.get_preferences()
    language = app_settings.target_language
    mine = tuple(entry.show.title for entry in library.mine(language))
    languages = ConversationLanguages.of(language, app_settings.native_language)
    avoid = tuple(req.avoid_titles)
    return SuggestionContext(
        avoid, preferences.interests, mine, languages, preferences.learner_name
    )


@discovery_router.post("/shows/discover", response_model=DiscoverResponse)
def discover_shows(
    context: SuggestionContext = Depends(_context),
    discovery: ShowDiscovery = Depends(get_show_discovery),
):
    try:
        shows = discovery.suggest(context)
    except NotEnoughSuggestions as too_few:
        raise HTTPException(UNAVAILABLE_STATUS, NOT_ENOUGH) from too_few
    language = context.languages.target_code
    drafts = [show_draft(show, show.hosts, language, SUGGESTED_SOURCE) for show in shows]
    return DiscoverResponse(suggestions=drafts)
