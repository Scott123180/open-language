from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from app.services.factory import get_app_settings, get_storage
from app.services.storage.base import AppSettingsRecord, StorageProvider

router = APIRouter(tags=["vocabulary"])


class SaveVocabularyRequest(BaseModel):
    word: str
    translation: str
    source_conversation_id: int | None = None


class SaveVocabularyResponse(BaseModel):
    id: int
    word: str
    translation: str
    target_language: str
    native_language: str
    source_conversation_id: int | None
    already_saved: bool


@router.post("/vocabulary", status_code=status.HTTP_201_CREATED)
def save_vocabulary(
    req: SaveVocabularyRequest,
    response: Response,
    storage: StorageProvider = Depends(get_storage),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
) -> SaveVocabularyResponse:
    item = storage.save_vocabulary_item(
        word=req.word,
        translation=req.translation,
        target_language=app_settings.target_language,
        native_language=app_settings.native_language,
        source_conversation_id=req.source_conversation_id,
    )
    if item.already_saved:
        response.status_code = status.HTTP_200_OK
    return SaveVocabularyResponse(
        id=item.id,
        word=item.word,
        translation=item.translation,
        target_language=item.target_language,
        native_language=item.native_language,
        source_conversation_id=item.source_conversation_id,
        already_saved=item.already_saved,
    )


@router.get("/vocabulary")
def list_vocabulary(storage: StorageProvider = Depends(get_storage)):
    return storage.list_vocabulary()
