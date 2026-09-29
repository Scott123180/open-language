"""/api/podcasts/hosts/shuffle and /api/podcasts/voice-sample: shaping hosts (contracts §4, §5).

A shuffled host is cast by code, like every host. A voice sample is the language's sample line
with the host's name, spoken in that voice only, and cached by (voice, name) so a second play
does not synthesise again. A voice that is not installed is a plain 503, never another voice.
"""

import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.podcasts.catalog import HOST_NAME_MAX_LENGTH
from app.podcasts.responses import host_draft
from app.podcasts.schemas import LANGUAGE_CHANGED, HostDraftModel, ShuffleHostRequest
from app.podcasts.services.casting import Host, HostCaster, InvalidCast
from app.podcasts.services.speaker_views import host_voice_unavailable_message
from app.practice_languages import language_name, voice_sample_line
from app.services.factory import get_app_settings, get_host_caster, get_speech_for_language
from app.services.storage.base import AppSettingsRecord
from app.services.tts.selection import SpeechForLanguage
from app.services.tts.voices import AVAILABLE_VOICES, VoiceInfo

host_router = APIRouter(tags=["podcasts"])

WAV_MEDIA_TYPE = "audio/wav"
UNKNOWN_VOICE = "That voice isn't one the app knows. Pick a host from the list."
INVALID_STATUS = 422
_VOICES = {voice.key: voice for voice in AVAILABLE_VOICES}


def get_sample_cache_dir() -> Path:
    """Where voice samples are kept; tests point it at a scratch directory."""
    return Path.home() / ".open-language" / "tts_cache" / "voice_samples"


@host_router.post("/hosts/shuffle", response_model=HostDraftModel)
def shuffle_host(
    req: ShuffleHostRequest,
    app_settings: AppSettingsRecord = Depends(get_app_settings),
    caster: HostCaster = Depends(get_host_caster),
):
    if req.language != app_settings.target_language:
        raise HTTPException(INVALID_STATUS, LANGUAGE_CHANGED)
    hosts = tuple(_host(draft, req.language) for draft in req.hosts)
    return host_draft(caster.recast(req.slot, hosts, req.learner_name))


@host_router.get("/voice-sample")
def voice_sample(
    voice_key: str,
    name: str = Query(min_length=1, max_length=HOST_NAME_MAX_LENGTH),
    speech: SpeechForLanguage = Depends(get_speech_for_language),
    cache_dir: Path = Depends(get_sample_cache_dir),
):
    voice = _known_voice(voice_key)
    unavailable = host_voice_unavailable_message(name)
    provider = speech.provider_for_voice(voice.language, voice.key, unavailable)
    path = cache_dir / _sample_file_name(voice.key, name)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        provider.synthesize(voice_sample_line(voice.language, name), path)
    return FileResponse(str(path), media_type=WAV_MEDIA_TYPE)


def _host(draft: HostDraftModel, language: str) -> Host:
    if _known_voice(draft.voice_key).language != language:
        raise HTTPException(
            INVALID_STATUS, f"{draft.name}: that voice doesn't speak {language_name(language)}."
        )
    try:
        return Host(draft.slot, draft.name, draft.personality_id, draft.voice_key, draft.show_role)
    except InvalidCast as invalid:
        raise HTTPException(INVALID_STATUS, str(invalid)) from invalid


def _known_voice(voice_key: str) -> VoiceInfo:
    if voice_key not in _VOICES:
        raise HTTPException(INVALID_STATUS, UNKNOWN_VOICE)
    return _VOICES[voice_key]


def _sample_file_name(voice_key: str, name: str) -> str:
    """A name can hold any character, so the file is named by a digest of it."""
    digest = hashlib.sha256(name.encode()).hexdigest()[:16]
    return f"{voice_key}-{digest}.wav"
