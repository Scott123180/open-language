"""Contract tests for CorrectionStorageProvider (contracts/api.md §3.4)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.corrections.services.sqlite_storage import SQLiteCorrectionStorageProvider
from app.corrections.services.storage import (
    CorrectionStorageProvider,
    FeedbackDraft,
    PauseSnapshot,
)
from app.database import Base
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageRole


def _configure_sqlite(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture()
def storage(tmp_path: Path):
    import app.corrections.models  # noqa: F401 — registers the correction tables
    import app.models.app_settings  # noqa: F401
    import app.models.conversation  # noqa: F401
    import app.models.learning_tool_result  # noqa: F401
    import app.models.message  # noqa: F401
    import app.models.vocabulary_item  # noqa: F401

    engine = create_engine(f"sqlite:///{tmp_path / 'contract.db'}")
    event.listen(engine, "connect", _configure_sqlite)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield SQLiteCorrectionStorageProvider(session)
    session.close()


def _seed_conversation(storage: SQLiteCorrectionStorageProvider) -> int:
    session = storage._db
    conv = Conversation(
        scenario_id="s1",
        scenario_title="Cafe",
        target_language="es",
        native_language="en",
        llm_model="llama3.1",
        status=ConversationStatus.ACTIVE,
        started_at=datetime.now(UTC),
    )
    session.add(conv)
    session.commit()
    return conv.id


def _seed_message(storage: SQLiteCorrectionStorageProvider, conversation_id: int) -> int:
    session = storage._db
    msg = Message(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content="Yo tener veinte años",
        created_at=datetime.now(UTC),
    )
    session.add(msg)
    session.commit()
    return msg.id


def _correction(rank: int = 0) -> FeedbackDraft:
    return FeedbackDraft(
        kind="correction",
        category="conjugation",
        error_fragment="Yo tener",
        corrected_text="Yo tengo veinte años",
        explanation="Tener must be conjugated as tengo with yo.",
        mode="strict",
        rank=rank,
    )


def test_provider_implements_the_abstraction(storage) -> None:
    assert isinstance(storage, CorrectionStorageProvider)


def test_get_pause_state_returns_zeroed_snapshot_for_unknown_conversation(storage) -> None:
    snapshot = storage.get_pause_state(9999)

    assert snapshot == PauseSnapshot(
        consecutive_corrected_attempts=0, awaiting_clarification=False, awaiting_retry=False
    )


def test_get_pause_state_does_not_create_a_row(storage) -> None:
    from app.corrections.models import ConversationCorrectionState

    storage.get_pause_state(9999)

    assert storage._db.query(ConversationCorrectionState).count() == 0


def test_save_feedback_returns_persisted_records(storage) -> None:
    conv_id = _seed_conversation(storage)
    msg_id = _seed_message(storage, conv_id)

    records = storage.save_feedback(msg_id, [_correction()])

    assert len(records) == 1
    assert records[0].id is not None
    assert records[0].message_id == msg_id
    assert records[0].corrected_text == "Yo tengo veinte años"


def test_save_feedback_is_insert_only(storage) -> None:
    conv_id = _seed_conversation(storage)
    msg_id = _seed_message(storage, conv_id)

    first = storage.save_feedback(msg_id, [_correction()])
    second = storage.save_feedback(msg_id, [_correction(rank=1)])

    assert first[0].id != second[0].id
    assert len(storage.list_feedback(conv_id)) == 2


def test_list_feedback_orders_by_message_then_rank(storage) -> None:
    conv_id = _seed_conversation(storage)
    first_msg = _seed_message(storage, conv_id)
    second_msg = _seed_message(storage, conv_id)

    storage.save_feedback(second_msg, [_correction(rank=1), _correction(rank=0)])
    storage.save_feedback(first_msg, [_correction(rank=0)])

    records = storage.list_feedback(conv_id)

    assert [(r.message_id, r.rank) for r in records] == [
        (first_msg, 0),
        (second_msg, 0),
        (second_msg, 1),
    ]


def test_list_feedback_is_empty_for_an_uncorrected_conversation(storage) -> None:
    conv_id = _seed_conversation(storage)

    assert storage.list_feedback(conv_id) == []


def test_set_pause_state_creates_then_updates_a_single_row(storage) -> None:
    from app.corrections.models import ConversationCorrectionState

    conv_id = _seed_conversation(storage)

    storage.set_pause_state(conv_id, attempts=1, awaiting_clarification=False)
    snapshot = storage.set_pause_state(conv_id, attempts=2, awaiting_clarification=True)

    assert snapshot.consecutive_corrected_attempts == 2
    assert snapshot.awaiting_clarification is True
    assert storage._db.query(ConversationCorrectionState).count() == 1


def test_pause_state_survives_a_reload(storage) -> None:
    conv_id = _seed_conversation(storage)
    storage.set_pause_state(conv_id, attempts=1, awaiting_clarification=False)

    reloaded = SQLiteCorrectionStorageProvider(storage._db)

    assert reloaded.get_pause_state(conv_id).consecutive_corrected_attempts == 1
