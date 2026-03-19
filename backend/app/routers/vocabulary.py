from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.services.factory import get_app_settings, get_storage
from app.services.storage.base import AppSettingsRecord, StorageProvider

router = APIRouter(tags=["vocabulary"])


class SaveVocabularyRequest(BaseModel):
    word: str
    translation: str
    source_conversation_id: int | None = None


@router.post("/vocabulary", status_code=status.HTTP_201_CREATED)
def save_vocabulary(
    req: SaveVocabularyRequest,
    storage: StorageProvider = Depends(get_storage),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
):
    item = storage.save_vocabulary_item(
        word=req.word,
        translation=req.translation,
        target_language=app_settings.target_language,
        native_language=app_settings.native_language,
        source_conversation_id=req.source_conversation_id,
    )
    return item


@router.get("/vocabulary")
def list_vocabulary(storage: StorageProvider = Depends(get_storage)):
    return storage.list_vocabulary()
