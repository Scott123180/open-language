import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.flashcards.router import router as flashcards_router
from app.routers import audio, chat, conversations, learning, scenarios, vocabulary
from app.routers import settings as settings_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Open Language backend started")
    yield


app = FastAPI(title="Open Language", lifespan=lifespan)

app.include_router(scenarios.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(audio.router, prefix="/api")
app.include_router(learning.router, prefix="/api")
app.include_router(vocabulary.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(flashcards_router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error for %s", request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
