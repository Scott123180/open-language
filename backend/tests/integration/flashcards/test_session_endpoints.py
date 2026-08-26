"""Integration tests for deck and session API endpoints (T027).

Covers:
  POST /api/flashcards/decks
  POST /api/flashcards/sessions
  POST /api/flashcards/sessions/{id}/cards/{pos}
  POST /api/flashcards/sessions/{id}/end
  GET  /api/flashcards/sessions/{id}/summary
  GET  /api/flashcards/tts/{vocab_item_id}
"""

from datetime import UTC, datetime

import pytest

from app.models.vocabulary_item import VocabularyItem

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def two_words(db_session):
    words = [
        VocabularyItem(
            word="bonjour",
            translation="hello",
            target_language="fr",
            native_language="en",
            saved_at=datetime.now(UTC),
            classification="not_practiced",
            manual_override=False,
        ),
        VocabularyItem(
            word="merci",
            translation="thank you",
            target_language="fr",
            native_language="en",
            saved_at=datetime.now(UTC),
            classification="difficult",
            manual_override=False,
        ),
    ]
    for w in words:
        db_session.add(w)
    db_session.commit()
    for w in words:
        db_session.refresh(w)
    return words


@pytest.fixture()
def deck(client, two_words):
    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "not_practiced",
        },
    )
    assert res.status_code == 201
    return res.json()


@pytest.fixture()
def session(client, deck):
    res = client.post("/api/flashcards/sessions", json={"deck_id": deck["id"]})
    assert res.status_code == 201
    return res.json()


# ---------------------------------------------------------------------------
# POST /api/flashcards/decks
# ---------------------------------------------------------------------------


def test_create_deck_returns_201(client, two_words):
    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "not_practiced",
        },
    )
    assert res.status_code == 201


def test_create_deck_contains_cards(client, two_words):
    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "not_practiced",
        },
    )
    data = res.json()
    assert data["actual_size"] == 2
    assert len(data["cards"]) == 2


def test_create_deck_auto_generates_name(client, two_words):
    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "not_practiced",
        },
    )
    data = res.json()
    assert "Deck" in data["name"]


def test_create_deck_with_explicit_name(client, two_words):
    res = client.post(
        "/api/flashcards/decks",
        json={
            "name": "My Custom Deck",
            "size": 2,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "mixed_review",
        },
    )
    assert res.json()["name"] == "My Custom Deck"


def test_create_deck_size_adjusted_when_pool_too_small(client, two_words):
    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 50,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "not_practiced",
        },
    )
    data = res.json()
    assert data["actual_size"] == 2
    assert data["size_adjusted"] is True


# ---------------------------------------------------------------------------
# POST /api/flashcards/sessions
# ---------------------------------------------------------------------------


def test_start_session_returns_201(client, deck):
    res = client.post("/api/flashcards/sessions", json={"deck_id": deck["id"]})
    assert res.status_code == 201


def test_start_session_returns_session_data(client, deck):
    res = client.post("/api/flashcards/sessions", json={"deck_id": deck["id"]})
    data = res.json()
    assert data["deck_id"] == deck["id"]
    assert data["total_cards"] == 2
    assert data["practice_mode"] == "recall"
    assert "id" in data


def test_start_session_for_nonexistent_deck_returns_404(client):
    res = client.post("/api/flashcards/sessions", json={"deck_id": 9999})
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/flashcards/sessions/{id}/cards/{pos}
# ---------------------------------------------------------------------------


def test_record_card_result_returns_200(client, session):
    # last card position (0-indexed) — use explicit 0 for clarity
    res = client.post(
        f"/api/flashcards/sessions/{session['id']}/cards/0",
        json={"rating": "knew_it", "response_type": None, "user_response": None},
    )
    assert res.status_code == 200


def test_record_card_result_increments_cards_reviewed(client, session):
    client.post(
        f"/api/flashcards/sessions/{session['id']}/cards/0",
        json={"rating": "knew_it", "response_type": None, "user_response": None},
    )
    res = client.post(
        f"/api/flashcards/sessions/{session['id']}/cards/1",
        json={"rating": "didnt_know", "response_type": None, "user_response": None},
    )
    assert res.json()["cards_reviewed"] == 2


# ---------------------------------------------------------------------------
# POST /api/flashcards/sessions/{id}/end
# ---------------------------------------------------------------------------


def test_end_session_returns_summary(client, session):
    client.post(
        f"/api/flashcards/sessions/{session['id']}/cards/0",
        json={"rating": "knew_it", "response_type": None, "user_response": None},
    )
    res = client.post(
        f"/api/flashcards/sessions/{session['id']}/end",
        json={"completed": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session["id"]
    assert data["completed"] is True
    assert data["knew_it_count"] == 1


def test_end_session_with_all_ratings(client, session):
    client.post(
        f"/api/flashcards/sessions/{session['id']}/cards/0",
        json={"rating": "knew_it", "response_type": None, "user_response": None},
    )
    client.post(
        f"/api/flashcards/sessions/{session['id']}/cards/1",
        json={"rating": "guessed", "response_type": None, "user_response": None},
    )
    res = client.post(
        f"/api/flashcards/sessions/{session['id']}/end",
        json={"completed": True},
    )
    data = res.json()
    assert data["knew_it_count"] == 1
    assert data["guessed_count"] == 1
    assert data["didnt_know_count"] == 0


# ---------------------------------------------------------------------------
# GET /api/flashcards/sessions/{id}/summary
# ---------------------------------------------------------------------------


def test_get_session_summary(client, session):
    client.post(
        f"/api/flashcards/sessions/{session['id']}/cards/0",
        json={"rating": "didnt_know", "response_type": None, "user_response": None},
    )
    client.post(
        f"/api/flashcards/sessions/{session['id']}/end",
        json={"completed": False},
    )
    res = client.get(f"/api/flashcards/sessions/{session['id']}/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session["id"]
    assert data["didnt_know_count"] == 1
    assert "words_needing_work" in data


def test_session_summary_words_needing_work(client, session):
    # Rate card 0 as didnt_know
    client.post(
        f"/api/flashcards/sessions/{session['id']}/cards/0",
        json={"rating": "didnt_know", "response_type": None, "user_response": None},
    )
    client.post(
        f"/api/flashcards/sessions/{session['id']}/end",
        json={"completed": True},
    )
    res = client.get(f"/api/flashcards/sessions/{session['id']}/summary")
    data = res.json()
    assert len(data["words_needing_work"]) == 1
    assert data["words_needing_work"][0]["rating"] == "didnt_know"


# ---------------------------------------------------------------------------
# T073 — GET /sessions/{id}/encouragement  &  POST /sessions/{id}/missed-deck
# ---------------------------------------------------------------------------


def test_encouragement_returns_message(client, session):
    res = client.get(f"/api/flashcards/sessions/{session['id']}/encouragement")
    assert res.status_code == 200
    data = res.json()
    assert "message" in data
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0


def test_missed_deck_creates_deck_from_didnt_know(client, session):
    # Rate card 0 as didnt_know
    client.post(
        f"/api/flashcards/sessions/{session['id']}/cards/0",
        json={"rating": "didnt_know", "response_type": None, "user_response": None},
    )
    client.post(f"/api/flashcards/sessions/{session['id']}/end", json={"completed": True})

    res = client.post(f"/api/flashcards/sessions/{session['id']}/missed-deck")
    assert res.status_code == 201
    data = res.json()
    assert data["actual_size"] == 1  # Only the didnt_know word


def test_missed_deck_returns_422_when_no_didnt_know(client, session):
    # End session without rating any cards as didnt_know
    client.post(f"/api/flashcards/sessions/{session['id']}/end", json={"completed": True})
    res = client.post(f"/api/flashcards/sessions/{session['id']}/missed-deck")
    assert res.status_code in (400, 404, 422)


# ---------------------------------------------------------------------------
# GET /api/flashcards/tts/{vocab_item_id}
# ---------------------------------------------------------------------------


def test_tts_synthesizes_wav_on_first_request(client, two_words):
    word_id = two_words[0].id

    res = client.get(f"/api/flashcards/tts/{word_id}")

    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/wav"
    assert res.content.startswith(b"RIFF")


def test_tts_serves_the_cached_file_on_repeat_request(client, two_words):
    word_id = two_words[0].id
    first = client.get(f"/api/flashcards/tts/{word_id}")

    second = client.get(f"/api/flashcards/tts/{word_id}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.content == first.content


def test_tts_returns_404_for_missing_word(client):
    res = client.get("/api/flashcards/tts/9999")
    assert res.status_code == 404
