"""T079: SpeakerNames is a one-method consumer interface; the factory backs it with podcasts."""

from abc import ABC

from app.conversation_summary import SpeakerNames
from app.services import factory
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.support.scratch_database import make_session


def test_speaker_names_has_exactly_names_for():
    assert issubclass(SpeakerNames, ABC)
    assert SpeakerNames.__abstractmethods__ == frozenset({"names_for"})


def test_the_factory_serves_podcast_names_for_a_roleplay_as_none(tmp_path):
    session = make_session(tmp_path / "names.db")
    conversations = SQLiteStorageProvider(session)
    roleplay = conversations.create_conversation("order-coffee", "Order a Coffee", "es", "en", "m")

    names = factory.get_speaker_names(factory.get_podcast_storage(session), conversations)

    assert isinstance(names, SpeakerNames)
    assert names.names_for(roleplay.id) is None
