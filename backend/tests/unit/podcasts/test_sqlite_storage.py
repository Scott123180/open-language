"""T010: the SQLite podcast storage (data-model §2.1–§2.4)."""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.podcasts.catalog import PODCAST_SCENARIO_ID
from app.podcasts.models import PodcastHost
from app.podcasts.services.sqlite_storage import SQLitePodcastStorage
from app.podcasts.services.storage import (
    NewEpisode,
    NewHost,
    NewHostLine,
    PreferencesRecord,
)
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.support.podcast_records import new_episode, new_host
from tests.support.scratch_database import make_session


@pytest.fixture
def session(tmp_path: Path):
    db_session = make_session(tmp_path / "podcasts.db")
    yield db_session
    db_session.close()


@pytest.fixture
def storage(session) -> SQLitePodcastStorage:
    return SQLitePodcastStorage(session)


@pytest.fixture
def core(session) -> SQLiteStorageProvider:
    return SQLiteStorageProvider(session)


def _panel(storage: SQLitePodcastStorage, **overrides):
    return storage.create_episode(new_episode(**overrides))


def _save_line(storage, episode, slot="lead", content="¡Hola!", **facts) -> object:
    host = next(h for h in storage.get_hosts(episode.conversation_id) if h.slot == slot)
    values = {"intent": "open", "invites_learner": False, "was_trimmed": False, **facts}
    return storage.save_host_line(
        NewHostLine(episode.conversation_id, host.host_id, content, **values)
    )


# --- episodes ---------------------------------------------------------------------------


def test_creating_an_episode_creates_its_conversation(storage, core):
    episode = _panel(storage, title="Weekend Food Talk", target_language="de")

    conversation = core.get_conversation(episode.conversation_id)

    assert conversation.scenario_id == PODCAST_SCENARIO_ID == "podcast"
    assert conversation.scenario_title == "Weekend Food Talk"
    assert conversation.target_language == "de"
    assert conversation.status == "active"


def test_the_episode_record_carries_the_show_and_format(storage):
    episode = _panel(storage, format="listen", length="short", learner_name="Sam")

    stored = storage.get_episode(episode.conversation_id)

    assert stored == episode
    assert (stored.format, stored.length, stored.learner_name) == ("listen", "short", "Sam")
    assert (stored.title, stored.show_id, stored.show_source) == (
        "Weekend Food Talk",
        "weekend-food-talk",
        "ready_made",
    )


def test_one_row_per_participating_host_is_stored(storage):
    episode = _panel(storage)

    hosts = storage.get_hosts(episode.conversation_id)

    assert [(h.slot, h.name) for h in hosts] == [("lead", "Lucía"), ("second", "Marco")]


def test_one_host_stores_only_the_lead(storage):
    episode = _panel(storage, format="one_host", hosts=(new_host("lead", "Lucía"),))

    assert [h.slot for h in storage.get_hosts(episode.conversation_id)] == ["lead"]


def test_an_unknown_episode_is_none(storage):
    assert storage.get_episode(999) is None


def test_a_roleplay_conversation_is_not_an_episode(storage, core):
    conversation = core.create_conversation("order-coffee", "Order a Coffee", "es", "en", "m")

    assert storage.get_episode(conversation.id) is None


def test_episodes_are_listed_newest_first(storage):
    first = _panel(storage, title="First")
    second = _panel(storage, title="Second")

    listed = storage.list_episodes()

    assert [e.conversation_id for e in listed] == [
        second.conversation_id,
        first.conversation_id,
    ]


@pytest.mark.parametrize(
    "hosts",
    [
        (new_host("lead", "Lucía"), new_host("lead", "Marco", "joker")),
        (new_host("lead", "Lucía"), new_host("second", "Lucía", "joker")),
    ],
    ids=["same-slot", "same-name"],
)
def test_duplicate_hosts_are_rejected(storage, session, hosts):
    with pytest.raises(IntegrityError):
        storage.create_episode(new_episode(hosts=hosts))
    session.rollback()


def test_a_failed_episode_leaves_no_conversation_behind(storage, session, core):
    duplicate = (new_host("lead", "Lucía"), new_host("second", "Lucía", "joker"))

    with pytest.raises(IntegrityError):
        storage.create_episode(new_episode(hosts=duplicate))
    session.rollback()

    assert core.list_conversations() == []


# --- lines ------------------------------------------------------------------------------


def test_a_host_line_is_an_assistant_message_with_its_host_facts(storage, core):
    episode = _panel(storage)

    line = _save_line(
        storage,
        episode,
        "second",
        "Hola, soy Marco.",
        intent="greet",
        **{
            "invites_learner": True,
            "was_trimmed": True,
        },
    )

    message = core.get_message(line.message_id)
    assert (message.role, message.content) == ("assistant", "Hola, soy Marco.")
    second = storage.get_hosts(episode.conversation_id)[1]
    assert line.host.host_id == second.host_id
    assert (line.host.intent, line.host.invites_learner, line.host.was_trimmed) == (
        "greet",
        True,
        True,
    )
    assert (line.host.is_passed, line.host.is_revealed) == (False, False)


def test_lines_are_the_messages_in_order_joined_to_their_hosts(storage, core):
    episode = _panel(storage)
    opening = _save_line(storage, episode, "lead", "¡Bienvenidos!")
    learner = core.save_message(episode.conversation_id, "user", "Hola a todos")
    reply = _save_line(storage, episode, "second", "¡Hola!", intent="discuss")

    lines = storage.get_lines(episode.conversation_id)

    assert [line.message_id for line in lines] == [opening.message_id, learner.id, reply.message_id]
    assert [line.is_host for line in lines] == [True, False, True]
    assert lines[1].host is None
    assert (lines[1].role, lines[1].content) == ("user", "Hola a todos")


def test_mark_passed_sets_the_flag(storage):
    episode = _panel(storage)
    line = _save_line(storage, episode, invites_learner=True)

    storage.mark_passed(line.message_id)

    assert storage.get_lines(episode.conversation_id)[0].host.is_passed is True


def test_mark_revealed_sets_the_flag_and_is_idempotent(storage):
    episode = _panel(storage)
    line = _save_line(storage, episode)

    assert storage.mark_revealed(episode.conversation_id, line.message_id) is True
    assert storage.mark_revealed(episode.conversation_id, line.message_id) is True

    assert storage.get_lines(episode.conversation_id)[0].host.is_revealed is True


def test_mark_revealed_refuses_a_learner_message(storage, core):
    episode = _panel(storage)
    learner = core.save_message(episode.conversation_id, "user", "Hola")

    assert storage.mark_revealed(episode.conversation_id, learner.id) is False


def test_mark_revealed_refuses_another_episodes_line(storage):
    first = _panel(storage)
    other = _panel(storage)
    line = _save_line(storage, other)

    assert storage.mark_revealed(first.conversation_id, line.message_id) is False


# --- preferences ------------------------------------------------------------------------


def test_preferences_are_created_with_their_defaults_on_first_read(storage, session):
    assert storage.get_preferences() == PreferencesRecord(
        last_format="one_host", is_show_text_on=False, interests=(), learner_name=None
    )
    assert session.execute(text("SELECT id FROM podcast_preferences")).scalar_one() == 1


def test_preferences_round_trip(storage):
    saved = PreferencesRecord(
        last_format="panel",
        is_show_text_on=True,
        interests=("football", "cooking"),
        learner_name="Sam",
    )

    storage.save_preferences(saved)

    assert storage.get_preferences() == saved


# --- cascade ----------------------------------------------------------------------------


def test_deleting_the_conversation_removes_every_episode_row(storage, session):
    episode = _panel(storage)
    _save_line(storage, episode)

    session.execute(
        text("DELETE FROM conversations WHERE id = :id"), {"id": episode.conversation_id}
    )
    session.commit()

    for table in ("podcast_episodes", "podcast_hosts", "podcast_host_lines"):
        assert session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0, table


def test_new_episode_and_new_host_are_value_objects():
    host = NewHost("lead", "Lucía", "enthusiast", "es_AR-daniela-high", "host")

    assert host.angle is None
    assert isinstance(new_episode(), NewEpisode)
    assert PodcastHost.__tablename__ == "podcast_hosts"
