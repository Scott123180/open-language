"""010 T037: ShowLibrary turns drafts into kept shows (research R1)."""

import pytest

from app.podcasts.schemas import ShowDraftModel
from app.podcasts.services.library import ShowLibrary, ShowNoLongerKept
from tests.support.fake_series_storage import FakeShowLibraryStorage

HOSTS = [
    {
        "slot": "lead",
        "name": "Hugo",
        "personality_id": "storyteller",
        "voice_key": "es_ES-davefx-medium",
        "show_role": "host",
        "angle": "Misses home.",
    },
    {
        "slot": "second",
        "name": "Inés",
        "personality_id": "dry_sceptic",
        "voice_key": "es_AR-daniela-high",
        "show_role": "co_host",
        "angle": None,
    },
]


def _draft(source: str = "ready_made", **changes) -> ShowDraftModel:
    values = {
        "source": source,
        "show_id": "big-little-questions" if source == "ready_made" else None,
        "title": "Night Shift Abroad",
        "premise": "Two nurses swap stories.",
        "topic": "living abroad",
        "learner_role": "caller",
        "language": "es",
        "hosts": HOSTS,
    }
    return ShowDraftModel(**{**values, **changes})


@pytest.fixture
def storage() -> FakeShowLibraryStorage:
    return FakeShowLibraryStorage()


@pytest.fixture
def library(storage) -> ShowLibrary:
    return ShowLibrary(storage)


def test_keeping_a_ready_made_draft_keeps_its_template(library, storage):
    kept = library.keep(_draft())

    assert kept.ref.template_id == "big-little-questions"
    assert kept.title == "Big Little Questions"


def test_keeping_a_learner_made_draft_keeps_its_content_and_personalities(library, storage):
    kept = library.keep(_draft("generated"))

    assert (kept.title, kept.premise, kept.topic, kept.learner_role) == (
        "Night Shift Abroad",
        "Two nurses swap stories.",
        "living abroad",
        "caller",
    )
    assert kept.personalities == ("storyteller", "dry_sceptic")
    assert kept.angles == ("Misses home.", None)


def test_keeping_a_kept_draft_returns_the_same_show(library):
    kept = library.keep(_draft("surprise"))

    assert library.keep(_draft("surprise", saved_show_id=kept.show_row_id)) == kept


def test_playing_a_show_touches_it(library, storage):
    kept = library.keep(_draft())

    library.played(kept)

    assert storage.played == [kept.show_row_id]


def test_resolving_an_unknown_saved_show_is_refused(library):
    with pytest.raises(ShowNoLongerKept, match="That show isn't kept any more. Pick another one."):
        library.resolve(_draft("generated", saved_show_id=99))


def test_resolving_an_unsaved_learner_made_draft_finds_nothing(library):
    assert library.resolve(_draft("suggested")) is None


def test_resolving_a_ready_made_show_never_kept_finds_nothing(library):
    assert library.resolve(_draft()) is None


def test_unfavouriting_an_unsaved_draft_finds_the_show_kept_with_its_content(library, storage):
    kept = library.favourite(_draft("suggested"), True)

    library.favourite(_draft("suggested"), False)

    assert storage.shows[kept.show_row_id].is_favourite is False


def test_unfavouriting_an_unsaved_draft_never_kept_finds_nothing(library):
    assert library.favourite(_draft("suggested"), False) is None
