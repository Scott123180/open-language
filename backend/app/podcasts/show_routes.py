"""/api/podcasts/shows: a show from the learner's idea, or a surprise (contracts §3).

Both return a draft and store nothing. A blank or long idea is refused before any model call,
and a declined idea gets a fixed plain message with the offer of Surprise me (FR-024).
"""

import random

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.podcasts.responses import show_draft
from app.podcasts.schemas import GenerateShowRequest, ShowDraftModel, ShowRefusal
from app.podcasts.services.casting import HostCaster
from app.podcasts.services.generator import GeneratedShow, ShowDeclined, ShowGenerator, ShowIdea
from app.podcasts.services.storage import PodcastStorage
from app.podcasts.services.surprise import RecentSurprises, SurpriseTopics
from app.practice_languages import ConversationLanguages
from app.services.factory import (
    get_app_settings,
    get_host_caster,
    get_podcast_storage,
    get_recent_surprises,
    get_structured_llm,
)
from app.services.llm.base import StructuredLLMProvider
from app.services.storage.base import AppSettingsRecord

show_router = APIRouter(tags=["podcasts"])

IDEA_MAX_LENGTH = 200
IDEA_NEEDED = "Type a few words about the show you'd like, or press Surprise me."
IDEA_DECLINED = "That idea can't become a show here. Try a different topic, or press Surprise me."
SURPRISE_FAILED = "Surprise me didn't find a show this time. Please try again."
GENERATED_SOURCE, SURPRISE_SOURCE = "generated", "surprise"
REFUSED_STATUS, SURPRISE_FAILED_STATUS = 422, 503


def get_show_generator(
    structured_llm: StructuredLLMProvider = Depends(get_structured_llm),
    caster: HostCaster = Depends(get_host_caster),
) -> ShowGenerator:
    return ShowGenerator(structured_llm, caster)


def get_surprise_topics() -> SurpriseTopics:
    """Fresh randomness per request; tests inject a seeded one."""
    return SurpriseTopics(random.Random())


def _base_idea(
    app_settings: AppSettingsRecord = Depends(get_app_settings),
    podcasts: PodcastStorage = Depends(get_podcast_storage),
) -> ShowIdea:
    """The learner's standing context for any show: languages, interests and name."""
    preferences = podcasts.get_preferences()
    languages = ConversationLanguages.of(app_settings.target_language, app_settings.native_language)
    return ShowIdea("", languages, tuple(preferences.interests), (), preferences.learner_name)


@show_router.post(
    "/shows/generate",
    response_model=ShowDraftModel,
    responses={REFUSED_STATUS: {"model": ShowRefusal}},
)
def generate_show(
    req: GenerateShowRequest,
    base: ShowIdea = Depends(_base_idea),
    generator: ShowGenerator = Depends(get_show_generator),
):
    idea = req.idea.strip()
    if not idea or len(idea) > IDEA_MAX_LENGTH:
        return _refusal(IDEA_NEEDED)
    request = _with_idea(base, idea, tuple(req.avoid_titles))
    try:
        return _draft(generator.generate(request), request, GENERATED_SOURCE)
    except ShowDeclined:
        return _refusal(IDEA_DECLINED)


@show_router.post("/shows/surprise", response_model=ShowDraftModel)
def surprise_show(
    base: ShowIdea = Depends(_base_idea),
    generator: ShowGenerator = Depends(get_show_generator),
    topics: SurpriseTopics = Depends(get_surprise_topics),
    recent: RecentSurprises = Depends(get_recent_surprises),
):
    surprise = recent.fresh(lambda: topics.draw(base.interests))
    request = _with_idea(base, surprise.idea, ())
    try:
        return _draft(generator.generate(request), request, SURPRISE_SOURCE)
    except ShowDeclined as declined:
        raise HTTPException(SURPRISE_FAILED_STATUS, SURPRISE_FAILED) from declined


def _with_idea(base: ShowIdea, idea: str, avoid_titles: tuple[str, ...]) -> ShowIdea:
    return ShowIdea(idea, base.languages, base.interests, avoid_titles, base.learner_name)


def _draft(show: GeneratedShow, request: ShowIdea, source: str) -> ShowDraftModel:
    return show_draft(show, show.hosts, request.languages.target_code, source)


def _refusal(detail: str) -> JSONResponse:
    content = ShowRefusal(detail=detail, can_surprise=True).model_dump()
    return JSONResponse(status_code=REFUSED_STATUS, content=content)
