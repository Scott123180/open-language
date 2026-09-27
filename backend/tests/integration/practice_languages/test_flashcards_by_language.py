"""T081: flashcards show one language at a time (contracts §8, SC-006, FR-020 – FR-023)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services.factory import get_llm
from app.services.llm.base import ChatMessage, LLMProvider
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.integration.conftest import _configure_sqlite
from tests.support.fake_speech import override_speech

OTHER_LANGUAGE_WORDS = "Some selected words are in another language. Reload the word list."
WORDS = {"es": ("casa", "perro", "Haus"), "de": ("Haus", "Hund", "Straße")}


class StubLLM(LLMProvider):
    @property
    def model_name(self) -> str:
        return "stub"

    def chat(self, messages: list[ChatMessage]) -> str:
        return "Ein ___ Satz."

    def chat_stream(self, messages: list[ChatMessage]):
        yield "stub"


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    event.listen(engine, "connect", _configure_sqlite)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()


@pytest.fixture
def client(session):
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_llm] = StubLLM
    override_speech(app)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def word_ids(session) -> dict[str, dict[str, int]]:
    """The same three-word vocabulary in each language; "Haus" is saved in both."""
    storage = SQLiteStorageProvider(session)
    return {
        language: {
            word: storage.save_vocabulary_item(word, "t", language, "en").id for word in words
        }
        for language, words in WORDS.items()
    }


def _deck(client, language: str, **body) -> dict:
    payload = {"practice_mode": "recall", "algorithm": "mixed_review", "size": 10}
    response = client.post("/api/flashcards/decks", json={**payload, **body, "language": language})
    assert response.status_code == 201, response.text
    return response.json()


def _practise(client, deck_id: int, rating: str = "didnt_know") -> int:
    session_id = client.post("/api/flashcards/sessions", json={"deck_id": deck_id}).json()["id"]
    client.post(f"/api/flashcards/sessions/{session_id}/cards/0", json={"rating": rating})
    return session_id


@pytest.fixture
def practised(client, word_ids) -> dict[str, int]:
    """A finished session on a deck in each language."""
    sessions = {}
    for language in WORDS:
        deck = _deck(client, language, word_source="all")
        sessions[language] = _practise(client, deck["id"])
        client.post(f"/api/flashcards/sessions/{sessions[language]}/end", json={"completed": True})
    return sessions


def _words(client, language: str) -> set[str]:
    words = client.get("/api/flashcards/words", params={"language": language}).json()
    return {(w["word"], w["target_language"]) for w in words}


@pytest.mark.parametrize("language", list(WORDS))
def test_the_word_list_shows_one_language(client, word_ids, language):
    assert _words(client, language) == {(word, language) for word in WORDS[language]}


@pytest.mark.parametrize("language", list(WORDS))
def test_the_deck_list_shows_one_language(client, practised, language):
    decks = client.get("/api/flashcards/decks", params={"language": language}).json()

    assert [deck["target_language"] for deck in decks] == [language]


@pytest.mark.parametrize("language", list(WORDS))
def test_analytics_count_one_language(client, practised, language):
    summary = client.get(
        "/api/flashcards/analytics", params={"language": language, "range": "all"}
    ).json()

    assert summary["at_a_glance"]["total_words"] == 3
    assert [p["session_id"] for p in summary["accuracy_trend"]] == [practised[language]]
    assert sum(summary["classification_now"].values()) == 3


@pytest.mark.parametrize(
    "path", ["/api/flashcards/words", "/api/flashcards/decks", "/api/flashcards/analytics"]
)
@pytest.mark.parametrize("params", [{}, {"language": "fr"}])
def test_a_collection_without_a_known_language_is_422(client, path, params):
    assert client.get(path, params=params).status_code == 422


@pytest.mark.parametrize("language", [None, "fr"])
def test_creating_a_deck_without_a_known_language_is_422(client, word_ids, language):
    body = {"practice_mode": "recall", "algorithm": "mixed_review", "size": 3, "word_source": "all"}
    if language:
        body["language"] = language

    assert client.post("/api/flashcards/decks", json=body).status_code == 422


@pytest.mark.parametrize("source", [{"word_source": "all"}, {"word_source": "filtered"}])
def test_a_german_deck_draws_only_german_words(client, word_ids, source):
    deck = _deck(client, "de", **source)

    assert deck["target_language"] == "de"
    assert {card["word"] for card in deck["cards"]} == set(WORDS["de"])


def test_selecting_a_word_in_another_language_is_422(client, word_ids):
    body = {
        "practice_mode": "recall",
        "algorithm": "mixed_review",
        "size": 2,
        "word_source": "selected",
        "selected_word_ids": [word_ids["de"]["Hund"], word_ids["es"]["perro"]],
        "language": "de",
    }

    response = client.post("/api/flashcards/decks", json=body)

    assert (response.status_code, response.json()) == (422, {"detail": OTHER_LANGUAGE_WORDS})


def test_refreshing_a_spanish_deck_draws_spanish_words_while_german_is_selected(client, word_ids):
    deck = _deck(client, "es", word_source="all")
    client.put("/api/settings", json={"target_language": "de"})

    refreshed = client.post(f"/api/flashcards/decks/{deck['id']}/refresh").json()

    assert {card["word"] for card in refreshed["cards"]} <= set(WORDS["es"])


class TestASpanishSessionFinishedWhileGermanIsSelected:
    @pytest.fixture
    def finished(self, client, word_ids, session):
        german_words = ", ".join(str(i) for i in word_ids["de"].values())
        session.execute(
            text(
                f"UPDATE vocabulary_items SET classification = 'learned' WHERE id IN ({german_words})"
            )
        )
        session.commit()
        deck = _deck(client, "es", word_source="all")
        session_id = client.post("/api/flashcards/sessions", json={"deck_id": deck["id"]}).json()[
            "id"
        ]
        client.put("/api/settings", json={"target_language": "de"})
        client.post(f"/api/flashcards/sessions/{session_id}/cards/0", json={"rating": "didnt_know"})
        summary = client.post(
            f"/api/flashcards/sessions/{session_id}/end", json={"completed": True}
        ).json()
        return session_id, summary

    def test_the_snapshot_counts_only_spanish_words(self, client, finished):
        snapshots = client.get(
            "/api/flashcards/analytics", params={"language": "es", "range": "all"}
        ).json()["classification_over_time"]

        [snapshot] = snapshots
        assert snapshot["learned"] == 0
        assert sum(snapshot[k] for k in ("not_practiced", "difficult", "almost_learned")) == 3

    def test_the_streak_counts_the_spanish_session(self, finished):
        _session_id, summary = finished

        assert summary["current_streak"] == 1

    def test_the_missed_deck_is_spanish(self, client, finished):
        session_id, _summary = finished

        missed = client.post(f"/api/flashcards/sessions/{session_id}/missed-deck").json()

        assert missed["target_language"] == "es"
        spanish_decks = client.get("/api/flashcards/decks", params={"language": "es"}).json()
        assert missed["id"] in {deck["id"] for deck in spanish_decks}


def test_the_same_spelling_has_its_own_classification_and_llm_cache(client, word_ids, session):
    german, spanish = word_ids["de"]["Haus"], word_ids["es"]["Haus"]
    client.patch(
        f"/api/flashcards/words/{german}/classification", json={"classification": "learned"}
    )
    for word_id in (german, spanish):
        client.get(f"/api/flashcards/words/{word_id}/info/meanings")

    classes = {
        w["id"]: w["classification"]
        for w in client.get("/api/flashcards/words", params={"language": "de"}).json()
    }
    cache_rows = session.execute(
        text("SELECT vocabulary_item_id, language FROM word_llm_cache ORDER BY vocabulary_item_id")
    ).fetchall()

    assert classes[german] == "learned"
    assert _words(client, "es") and spanish not in classes
    assert sorted(tuple(row) for row in cache_rows) == sorted([(german, "de"), (spanish, "es")])
