"""Practice-language data: the files under `languages/` and their strict loader.

A leaf package: it imports nothing from the rest of the app. `practice_languages` and
`services/tts` adapt its records to their own types. Code outside imports only this root.
"""

from app.language_data.loader import LanguageDataError, load_language_records, voice_keys
from app.language_data.records import LanguageRecord, PodcastRecord, VoiceRecord

__all__ = [
    "LanguageDataError",
    "LanguageRecord",
    "PodcastRecord",
    "VoiceRecord",
    "load_language_records",
    "voice_keys",
]
