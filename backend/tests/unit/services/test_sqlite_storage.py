import time
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.services.storage.sqlite import SQLiteStorageProvider


def _configure_sqlite(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture
def storage(tmp_path: Path) -> SQLiteStorageProvider:
    db_file = tmp_path / "unit_test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    event.listen(engine, "connect", _configure_sqlite)
    import app.models.app_settings  # noqa: F401
    import app.models.conversation  # noqa: F401
    import app.models.learning_tool_result  # noqa: F401
    import app.models.message  # noqa: F401
    import app.models.vocabulary_item  # noqa: F401

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)  # noqa: N806
    session = Session()
    yield SQLiteStorageProvider(session)
    session.close()


def _make_conv(storage: SQLiteStorageProvider, scenario_id: str = "s1"):
    return storage.create_conversation(
        scenario_id=scenario_id,
        scenario_title="Test Scenario",
        target_language="es",
        native_language="en",
        llm_model="llama3.1",
    )


def test_complete_conversation_sets_status_and_ended_at(storage: SQLiteStorageProvider) -> None:
    conv = _make_conv(storage)
    assert conv.ended_at is None
    assert conv.status == "active"
    completed = storage.complete_conversation(conv.id)
    assert completed.status == "completed"
    assert completed.ended_at is not None


def test_list_conversations_reverse_chronological(storage: SQLiteStorageProvider) -> None:
    c1 = _make_conv(storage, "s1")
    time.sleep(0.01)
    c2 = _make_conv(storage, "s2")
    time.sleep(0.01)
    c3 = _make_conv(storage, "s3")
    results = storage.list_conversations()
    ids = [r.id for r in results]
    assert ids == [c3.id, c2.id, c1.id]


def test_set_tts_path_updates_message_record(storage: SQLiteStorageProvider) -> None:
    conv = _make_conv(storage)
    msg = storage.save_message(conv.id, "assistant", "Hola")
    assert msg.tts_audio_path is None
    updated = storage.set_tts_path(msg.id, "/tmp/audio.wav")
    assert updated.tts_audio_path == "/tmp/audio.wav"
    messages = storage.get_messages(conv.id)
    assert messages[0].tts_audio_path == "/tmp/audio.wav"


def test_list_vocabulary_most_recently_saved_first(storage: SQLiteStorageProvider) -> None:
    storage.save_vocabulary_item("perro", "dog", "es", "en")
    time.sleep(0.01)
    storage.save_vocabulary_item("gato", "cat", "es", "en")
    time.sleep(0.01)
    storage.save_vocabulary_item("casa", "house", "es", "en")
    items = storage.list_vocabulary()
    words = [i.word for i in items]
    assert words == ["casa", "gato", "perro"]


# ---- get_or_create_learning_result caching tests (T079) ----


def test_get_or_create_calls_compute_once_on_first_call(storage: SQLiteStorageProvider) -> None:
    conv = _make_conv(storage)
    msg = storage.save_message(conv.id, "user", "Hola")
    call_count = 0

    def compute() -> str:
        nonlocal call_count
        call_count += 1
        return "result text"

    result = storage.get_or_create_learning_result(msg.id, "grammar", None, compute)

    assert result.result == "result text"
    assert call_count == 1


def test_get_or_create_does_not_call_compute_on_second_call(storage: SQLiteStorageProvider) -> None:
    conv = _make_conv(storage)
    msg = storage.save_message(conv.id, "user", "Hola")
    call_count = 0

    def compute() -> str:
        nonlocal call_count
        call_count += 1
        return "cached result"

    storage.get_or_create_learning_result(msg.id, "grammar", None, compute)
    assert call_count == 1

    result = storage.get_or_create_learning_result(msg.id, "grammar", None, compute)
    assert call_count == 1  # compute NOT called again
    assert result.result == "cached result"


def test_get_or_create_different_input_selection_calls_compute_separately(
    storage: SQLiteStorageProvider,
) -> None:
    conv = _make_conv(storage)
    msg = storage.save_message(conv.id, "user", "Tengo hambre y sed")
    call_count = 0

    def compute() -> str:
        nonlocal call_count
        call_count += 1
        return f"lookup result {call_count}"

    storage.get_or_create_learning_result(msg.id, "word_lookup", "hambre", compute)
    assert call_count == 1

    storage.get_or_create_learning_result(msg.id, "word_lookup", "sed", compute)
    assert call_count == 2


def test_fresh_settings_default_to_ollama_at_low_effort(storage: SQLiteStorageProvider) -> None:
    settings = storage.get_settings()

    assert settings.llm_provider == "ollama"
    assert settings.llm_effort == "low"


def test_update_settings_persists_provider_model_and_effort(
    storage: SQLiteStorageProvider,
) -> None:
    updated = storage.update_settings(
        llm_provider="claude", llm_model="sonnet", llm_effort="medium"
    )
    reread = storage.get_settings()

    assert (updated.llm_provider, updated.llm_model, updated.llm_effort) == (
        "claude",
        "sonnet",
        "medium",
    )
    assert (reread.llm_provider, reread.llm_model, reread.llm_effort) == (
        "claude",
        "sonnet",
        "medium",
    )


def test_fresh_settings_default_to_the_natural_conversation_level(
    storage: SQLiteStorageProvider,
) -> None:
    assert storage.get_settings().conversation_level == "natural"


def test_update_settings_persists_only_the_conversation_level(
    storage: SQLiteStorageProvider,
) -> None:
    before = storage.get_settings()

    updated = storage.update_settings(conversation_level="beginner")
    reread = storage.get_settings()

    assert updated.conversation_level == "beginner"
    assert reread.conversation_level == "beginner"
    assert replace(reread, conversation_level="natural", updated_at=before.updated_at) == before


# --- 006: per-language voice memory (T012) --------------------------------------------


def test_fresh_settings_have_no_voice_choices(storage: SQLiteStorageProvider) -> None:
    assert storage.get_settings().voice_choices == {}


def test_a_saved_voice_choice_is_read_back(storage: SQLiteStorageProvider) -> None:
    storage.save_voice_choice("de", "de_DE-kerstin-low")

    assert storage.get_settings().voice_choices == {"de": "de_DE-kerstin-low"}


def test_saving_again_updates_the_language_in_place(storage: SQLiteStorageProvider) -> None:
    from app.models.voice_choice import VoiceChoice

    storage.save_voice_choice("de", "de_DE-kerstin-low")
    storage.save_voice_choice("de", "de_DE-thorsten-medium")

    assert storage.get_settings().voice_choices == {"de": "de_DE-thorsten-medium"}
    assert storage._db.query(VoiceChoice).count() == 1


def test_saving_one_language_leaves_another_untouched(storage: SQLiteStorageProvider) -> None:
    storage.save_voice_choice("es", "es_AR-daniela-high")

    storage.save_voice_choice("de", "de_DE-kerstin-low")

    assert storage.get_settings().voice_choices == {
        "es": "es_AR-daniela-high",
        "de": "de_DE-kerstin-low",
    }


def test_the_settings_record_no_longer_carries_a_single_voice(
    storage: SQLiteStorageProvider,
) -> None:
    assert not hasattr(storage.get_settings(), "tts_voice")


def test_fresh_settings_summarise_in_the_conversations_language(storage) -> None:
    assert storage.get_settings().summary_language == "conversation"


def test_the_summary_language_round_trips(storage) -> None:
    storage.update_settings(summary_language="native")

    assert storage.get_settings().summary_language == "native"
