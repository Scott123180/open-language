import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.services.audio.conversion import convert_webm_to_wav
from app.services.factory import get_storage, get_stt, get_tts
from app.services.storage.base import StorageProvider
from app.services.stt.base import STTError, STTProvider
from app.services.tts.base import TTSProvider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["audio"])


@router.get("/audio/tts/{message_id}")
def get_tts_audio(
    message_id: int,
    storage: StorageProvider = Depends(get_storage),
    tts: TTSProvider = Depends(get_tts),
):
    message = storage.get_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    # If cached file exists, return it directly
    if message.tts_audio_path:
        cached = Path(message.tts_audio_path)
        if cached.exists():
            return FileResponse(str(cached), media_type="audio/wav")

    # Synthesize and cache
    cache_dir = Path.home() / ".open-language" / "tts_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    audio_path = cache_dir / f"{message_id}.wav"

    tts.synthesize(message.content, audio_path)
    storage.set_tts_path(message_id, str(audio_path))

    return FileResponse(str(audio_path), media_type="audio/wav")


@router.post("/audio/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    stt: STTProvider = Depends(get_stt),
):
    logger.debug("Transcription requested with language hint %r", language)
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    try:
        wav_path = convert_webm_to_wav(audio_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=422, detail="Audio processing failed. Please try again."
        ) from e

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, stt.transcribe, wav_path, language)
    except STTError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    finally:
        wav_path.unlink(missing_ok=True)

    if not result.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not understand audio. Please speak clearly and try again.",
        )

    return {"text": result.text, "detected_language": result.detected_language}
