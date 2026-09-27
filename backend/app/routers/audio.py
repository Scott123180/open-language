import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import get_settings
from app.practice_languages import PRACTICE_LANGUAGES
from app.services.audio.conversion import convert_webm_to_wav
from app.services.factory import get_speech_for_language, get_storage, get_stt
from app.services.storage.base import MessageRecord, StorageProvider
from app.services.stt.base import STTError, STTProvider, TranscriptionResult
from app.services.tts.selection import SpeechForLanguage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["audio"])

WAV_MEDIA_TYPE = "audio/wav"
UNSUPPORTED_LANGUAGE = "Unsupported language"


@router.get("/audio/tts/{message_id}")
def get_tts_audio(
    message_id: int,
    storage: StorageProvider = Depends(get_storage),
    speech: SpeechForLanguage = Depends(get_speech_for_language),
):
    message = storage.get_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    cached = _cached_wav(message)
    if cached is not None:
        return FileResponse(str(cached), media_type=WAV_MEDIA_TYPE)
    conversation = storage.get_conversation(message.conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    audio_path = _synthesize_and_cache(speech, storage, message, conversation.target_language)
    return FileResponse(str(audio_path), media_type=WAV_MEDIA_TYPE)


def _tts_cache_dir() -> Path:
    return Path.home() / ".open-language" / "tts_cache"


def _cached_wav(message: MessageRecord) -> Path | None:
    if message.tts_audio_path and Path(message.tts_audio_path).exists():
        return Path(message.tts_audio_path)
    return None


def _synthesize_and_cache(
    speech: SpeechForLanguage, storage: StorageProvider, message: MessageRecord, language: str
) -> Path:
    """Speak the message in its conversation's language; `VoiceUnavailable` becomes a 503."""
    provider = speech.provider_for(language)
    cache_dir = _tts_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    audio_path = cache_dir / f"{message.id}.wav"
    provider.synthesize(message.content, audio_path)
    storage.set_tts_path(message.id, str(audio_path))
    return audio_path


@router.post("/audio/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    stt: STTProvider = Depends(get_stt),
):
    logger.debug("Transcription requested with language hint %r", language)
    _require_supported_language(language)
    wav_path = _wav_from_upload(await file.read())
    result = await _transcribe_off_loop(stt, wav_path, language)
    if not result.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not understand audio. Please speak clearly and try again.",
        )
    return {
        "text": result.text,
        "detected_language": result.detected_language,
        "confidence": result.confidence,
        "is_low_confidence": _is_low_confidence(result.confidence),
    }


def _require_supported_language(language: str | None) -> None:
    """The hint is a practice-language code; absent means auto-detect (research R7)."""
    if language is not None and language not in PRACTICE_LANGUAGES:
        raise HTTPException(status_code=422, detail=UNSUPPORTED_LANGUAGE)


def _wav_from_upload(audio_bytes: bytes) -> Path:
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty")
    try:
        return convert_webm_to_wav(audio_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=422, detail="Audio processing failed. Please try again."
        ) from e


async def _transcribe_off_loop(
    stt: STTProvider, wav_path: Path, language: str | None
) -> TranscriptionResult:
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, stt.transcribe, wav_path, language)
    except STTError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    finally:
        wav_path.unlink(missing_ok=True)


def _is_low_confidence(confidence: float | None) -> bool:
    """None means "no information" and must never be gated (FR-010a); 0.0 must."""
    if confidence is None:
        return False
    return confidence < get_settings().low_confidence_threshold
