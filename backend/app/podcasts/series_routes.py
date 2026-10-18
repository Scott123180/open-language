"""/api/podcasts/series: a series' hosts and memory (010 contracts §5, §8).

The setup screen reads a series here and starts a memory catch-up when it opens. Before a
series Start it waits on the catch-up with `?wait=true`, in the thread pool FastAPI runs sync
endpoints on, so the event loop is never blocked (research R6).
"""

from functools import partial

from fastapi import APIRouter, Depends, HTTPException, Response

from app.podcasts.catalog import MEMORY_WAIT_SECONDS
from app.podcasts.responses import series_detail, show_listing
from app.podcasts.schemas import MemoryStatusResponse, SeriesDetailResponse
from app.podcasts.services.casting import HostCaster
from app.podcasts.services.library import ShowLibrary, ShowShelf
from app.podcasts.services.series import SeriesService
from app.podcasts.services.storage import PodcastStorage
from app.services.factory import (
    get_host_caster,
    get_memory_catch_ups,
    get_podcast_storage,
    get_series_memory_keeper,
    get_series_storage,
    get_show_library_storage,
    get_voice_installation,
)
from app.services.tts.base import VoiceInstallation
from app.services.tts.voices import voices_for

series_router = APIRouter(tags=["podcasts"])

SERIES_GONE = "That series isn't there any more. Open the show again."
ACCEPTED_STATUS = 202
UP_TO_DATE = "up_to_date"


def get_memory_wait_seconds() -> float:
    """How long a Start waits for the hosts to catch up; tests inject a short limit."""
    return MEMORY_WAIT_SECONDS


def installed_count(language: str, installation: VoiceInstallation) -> int:
    return sum(1 for voice in voices_for(language) if installation.is_installed(voice.key))


def get_series_service(
    library_storage=Depends(get_show_library_storage),
    series_storage=Depends(get_series_storage),
    installation: VoiceInstallation = Depends(get_voice_installation),
) -> SeriesService:
    counter = partial(installed_count, installation=installation)
    return SeriesService(ShowLibrary(library_storage), series_storage, counter)


def get_show_shelf(
    library_storage=Depends(get_show_library_storage),
    series_storage=Depends(get_series_storage),
    caster: HostCaster = Depends(get_host_caster),
) -> ShowShelf:
    return ShowShelf(library_storage, series_storage, caster)


def _require_series(series_storage, series_id: int):
    series = series_storage.get(series_id)
    if series is None:
        raise HTTPException(status_code=404, detail=SERIES_GONE)
    return series


@series_router.get("/series/{series_id}", response_model=SeriesDetailResponse)
def get_series(
    series_id: int,
    series_storage=Depends(get_series_storage),
    catch_ups=Depends(get_memory_catch_ups),
    shelf: ShowShelf = Depends(get_show_shelf),
    podcasts: PodcastStorage = Depends(get_podcast_storage),
    installation: VoiceInstallation = Depends(get_voice_installation),
):
    series = _require_series(series_storage, series_id)
    learner_name = podcasts.get_preferences().learner_name
    item = shelf.item(series.show, series, learner_name, series.language)
    status = catch_ups.status(series_id, series_storage)
    points = series_storage.remembered(series_id)
    return series_detail(series, points, status, show_listing(item, series.language), installation)


@series_router.post(
    "/series/{series_id}/memory",
    response_model=MemoryStatusResponse,
    response_model_exclude_none=True,
)
def catch_up_memory(
    series_id: int,
    response: Response,
    wait: bool = False,
    series_storage=Depends(get_series_storage),
    catch_ups=Depends(get_memory_catch_ups),
    keeper=Depends(get_series_memory_keeper),
    limit: float = Depends(get_memory_wait_seconds),
):
    """Start a catch-up (202), or with `wait` hold until it ends or times out (200)."""
    _require_series(series_storage, series_id)
    if wait:
        outcome = catch_ups.wait(series_id, keeper, limit)
        return MemoryStatusResponse(status=outcome.status, detail=outcome.detail)
    response.status_code = ACCEPTED_STATUS
    if catch_ups.status(series_id, series_storage) == UP_TO_DATE:
        return MemoryStatusResponse(status=UP_TO_DATE)
    return MemoryStatusResponse(status=catch_ups.start(series_id, keeper))
