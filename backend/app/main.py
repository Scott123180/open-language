import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.corrections.router import router as corrections_router
from app.database import init_db
from app.flashcards.router import router as flashcards_router
from app.podcasts import router as podcasts_router
from app.routers import audio, chat, conversations, learning, scenarios, vocabulary
from app.routers import settings as settings_router
from app.services.conversation import SESSION_REAPER_INTERVAL_SECONDS, run_session_reaper
from app.services.factory import get_conversation_engine
from app.services.llm.base import LLMError
from app.services.tts.base import VoiceUnavailable

LLM_UNAVAILABLE_STATUS = 503
VOICE_UNAVAILABLE_STATUS = 503
STATIC_DIR = Path(__file__).parent.parent / "static"

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    engine = get_conversation_engine()
    reaper = asyncio.create_task(run_session_reaper(engine, SESSION_REAPER_INTERVAL_SECONDS))
    logger.info("Open Language backend started")
    yield
    reaper.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await reaper
    # No conversation session, and so no `claude` process, outlives the backend.
    engine.close()


app = FastAPI(title="Open Language", lifespan=lifespan)

app.include_router(scenarios.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(audio.router, prefix="/api")
app.include_router(learning.router, prefix="/api")
app.include_router(vocabulary.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(flashcards_router, prefix="/api")
app.include_router(corrections_router, prefix="/api")
app.include_router(podcasts_router)


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    """Every provider failure reaches the learner as the provider's own next step (R-10)."""
    logger.warning("Language model request failed for %s: %s", request.url.path, exc)
    return JSONResponse(status_code=LLM_UNAVAILABLE_STATUS, content={"detail": exc.user_message})


@app.exception_handler(VoiceUnavailable)
async def voice_unavailable_handler(request: Request, exc: VoiceUnavailable) -> JSONResponse:
    """A missing voice is reported plainly; no other voice speaks instead (FR-018)."""
    logger.warning("No installed voice for %s: %s", request.url.path, exc.user_message)
    return JSONResponse(status_code=VOICE_UNAVAILABLE_STATUS, content={"detail": exc.user_message})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error for %s", request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


class FrontendBuildMissingError(RuntimeError):
    """Production mode was asked to serve a frontend that has not been built."""


def serve_built_frontend(app: FastAPI, static_dir: Path, settings: Settings) -> None:
    """Mount the built frontend at `/` in production; in development Vite serves it."""
    if not settings.is_production:
        return
    if not (static_dir / "index.html").exists():
        raise FrontendBuildMissingError(
            f"Production mode needs a built frontend in {static_dir}. "
            "Run `npm run build` in frontend/, or start with ./run.sh --prod."
        )
    # Registered after every /api router: a mount at `/` would otherwise shadow them.
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


serve_built_frontend(app, STATIC_DIR, get_settings())
