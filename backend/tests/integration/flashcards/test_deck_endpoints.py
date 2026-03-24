"""Integration tests for deck generation with each algorithm (T044).

Covers:
  - POST /api/flashcards/decks with each algorithm (not_practiced, difficult,
    previously_guessed, mixed_review)
  - Adjusted-size notification when pool < requested size
  - GET /api/flashcards/decks (list)
  - GET /api/flashcards/decks/{id}
  - PATCH /api/flashcards/decks/{id} (rename)
  - DELETE /api/flashcards/decks/{id}

T049 extends with:
  - POST /api/flashcards/decks in Listen, Produce, and Fill-in-the-Blank modes
  - fill_blank_sentence field on DeckCards for FitB decks

T081 extends with:
  - POST /api/flashcards/decks/{id}/refresh
"""

from datetime import UTC, datetime

import pytest

from app.models.vocabulary_item import VocabularyItem

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def seeded_words(db_session):
    """Seed words covering all 4 classifications for algorithm testing."""
    words = [
        VocabularyItem(
            word="np1",
            translation="not practiced 1",
            target_language="fr",
            native_language="en",
            saved_at=datetime.now(UTC),
            classification="not_practiced",
            manual_override=False,
        ),
        VocabularyItem(
            word="np2",
            translation="not practiced 2",
            target_language="fr",
            native_language="en",
            saved_at=datetime.now(UTC),
            classification="not_practiced",
            manual_override=False,
        ),
        VocabularyItem(
            word="d1",
            translation="difficult 1",
            target_language="fr",
            native_language="en",
            saved_at=datetime.now(UTC),
            classification="difficult",
            manual_override=False,
        ),
        VocabularyItem(
            word="d2",
            translation="difficult 2",
            target_language="fr",
            native_language="en",
            saved_at=datetime.now(UTC),
            classification="difficult",
            manual_override=False,
        ),
        VocabularyItem(
            word="al1",
            translation="almost learned 1",
            target_language="fr",
            native_language="en",
            saved_at=datetime.now(UTC),
            classification="almost_learned",
            manual_override=False,
        ),
        VocabularyItem(
            word="l1",
            translation="learned 1",
            target_language="fr",
            native_language="en",
            saved_at=datetime.now(UTC),
            classification="learned",
            manual_override=False,
        ),
    ]
    for w in words:
        db_session.add(w)
    db_session.commit()
    for w in words:
        db_session.refresh(w)
    return words


# ---------------------------------------------------------------------------
# Algorithm-specific deck generation
# ---------------------------------------------------------------------------


def test_not_practiced_algorithm_creates_deck(client, seeded_words):
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
    data = res.json()
    assert data["algorithm"] == "not_practiced"
    assert data["actual_size"] == 2


def test_difficult_algorithm_creates_deck(client, seeded_words):
    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "difficult",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["algorithm"] == "difficult"
    assert data["actual_size"] == 2


def test_previously_guessed_algorithm_creates_deck(client, seeded_words):
    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "previously_guessed",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["algorithm"] == "previously_guessed"


def test_mixed_review_algorithm_creates_deck(client, seeded_words):
    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 4,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "mixed_review",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["algorithm"] == "mixed_review"
    assert data["actual_size"] == 4


def test_size_adjusted_when_pool_smaller_than_requested(client, seeded_words):
    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 100,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "mixed_review",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["size_adjusted"] is True
    assert data["actual_size"] == len(seeded_words)


def test_deck_cards_are_subset_of_pool(client, seeded_words):
    pool_words = {w.word for w in seeded_words}
    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 4,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "mixed_review",
        },
    )
    data = res.json()
    for card in data["cards"]:
        assert card["word"] in pool_words


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


def test_list_decks(client, seeded_words):
    client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "not_practiced",
        },
    )
    client.post(
        "/api/flashcards/decks",
        json={"size": 2, "word_source": "all", "practice_mode": "recall", "algorithm": "difficult"},
    )
    res = client.get("/api/flashcards/decks")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_get_deck_by_id(client, seeded_words):
    create_res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "not_practiced",
        },
    )
    deck_id = create_res.json()["id"]
    res = client.get(f"/api/flashcards/decks/{deck_id}")
    assert res.status_code == 200
    assert res.json()["id"] == deck_id


def test_get_deck_404_for_missing(client):
    res = client.get("/api/flashcards/decks/9999")
    assert res.status_code == 404


def test_rename_deck(client, seeded_words):
    create_res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "not_practiced",
        },
    )
    deck_id = create_res.json()["id"]
    res = client.patch(f"/api/flashcards/decks/{deck_id}", json={"name": "My Renamed Deck"})
    assert res.status_code == 200
    assert res.json()["name"] == "My Renamed Deck"


def test_delete_deck(client, seeded_words):
    create_res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "not_practiced",
        },
    )
    deck_id = create_res.json()["id"]
    del_res = client.delete(f"/api/flashcards/decks/{deck_id}")
    assert del_res.status_code == 204
    get_res = client.get(f"/api/flashcards/decks/{deck_id}")
    assert get_res.status_code == 404


# ---------------------------------------------------------------------------
# T049 — Practice mode deck creation (Listen, Produce, Fill-in-the-Blank)
# ---------------------------------------------------------------------------


def test_listen_mode_deck_creation(client, seeded_words):
    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "listen",
            "algorithm": "not_practiced",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["practice_mode"] == "listen"
    assert len(data["cards"]) == 2


def test_produce_mode_deck_creation(client, seeded_words):
    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "produce",
            "algorithm": "not_practiced",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["practice_mode"] == "produce"
    assert len(data["cards"]) == 2


def test_fill_blank_mode_deck_creation(client, seeded_words):
    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "fill_blank",
            "algorithm": "not_practiced",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["practice_mode"] == "fill_blank"
    assert len(data["cards"]) == 2


def test_fill_blank_deck_cards_have_sentence_field(client, seeded_words):
    """DeckCard response includes fill_blank_sentence (may be None if LLM unavailable)."""
    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "fill_blank",
            "algorithm": "not_practiced",
        },
    )
    assert res.status_code == 201
    for card in res.json()["cards"]:
        assert "fill_blank_sentence" in card


def test_non_fill_blank_deck_cards_have_no_sentence(client, seeded_words):
    """DeckCards for non-FitB modes have fill_blank_sentence as None."""
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
    for card in res.json()["cards"]:
        assert card.get("fill_blank_sentence") is None


# ---------------------------------------------------------------------------
# T060 — SRS eligibility: due Learned words appear in decks; not-due excluded
# ---------------------------------------------------------------------------


def test_learned_word_past_due_appears_in_deck(client, db_session):
    """A Learned word with next_due_at in the past is eligible for deck selection."""
    from datetime import UTC, datetime, timedelta

    from app.flashcards.models import SpacedRepetitionSchedule
    from app.models.vocabulary_item import VocabularyItem

    past_due = VocabularyItem(
        word="past_due_word",
        translation="past due",
        target_language="fr",
        native_language="en",
        saved_at=datetime.now(UTC),
        classification="learned",
        manual_override=False,
    )
    db_session.add(past_due)
    db_session.commit()
    db_session.refresh(past_due)

    srs = SpacedRepetitionSchedule(
        vocabulary_item_id=past_due.id,
        interval_stage=1,
        last_practiced_at=datetime.now(UTC) - timedelta(days=5),
        next_due_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(srs)
    db_session.commit()

    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 10,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "mixed_review",
        },
    )
    assert res.status_code == 201
    card_words = [c["word"] for c in res.json()["cards"]]
    assert "past_due_word" in card_words


def test_learned_word_not_yet_due_excluded_from_deck(client, db_session):
    """A Learned word with next_due_at in the future is excluded from deck selection."""
    from datetime import UTC, datetime, timedelta

    from app.flashcards.models import SpacedRepetitionSchedule
    from app.models.vocabulary_item import VocabularyItem

    not_due = VocabularyItem(
        word="not_due_word",
        translation="not due",
        target_language="fr",
        native_language="en",
        saved_at=datetime.now(UTC),
        classification="learned",
        manual_override=False,
    )
    db_session.add(not_due)
    db_session.commit()
    db_session.refresh(not_due)

    srs = SpacedRepetitionSchedule(
        vocabulary_item_id=not_due.id,
        interval_stage=3,
        last_practiced_at=datetime.now(UTC) - timedelta(days=1),
        next_due_at=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add(srs)
    db_session.commit()

    res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 10,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "mixed_review",
        },
    )
    assert res.status_code == 201
    card_words = [c["word"] for c in res.json()["cards"]]
    assert "not_due_word" not in card_words


# ---------------------------------------------------------------------------
# T081 — POST /api/flashcards/decks/{id}/refresh
# ---------------------------------------------------------------------------


def test_refresh_deck_returns_200(client, seeded_words):
    create_res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 4,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "mixed_review",
        },
    )
    deck_id = create_res.json()["id"]
    res = client.post(f"/api/flashcards/decks/{deck_id}/refresh")
    assert res.status_code == 200


def test_refresh_preserves_deck_name_and_mode(client, seeded_words):
    create_res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "not_practiced",
            "name": "My Custom Deck",
        },
    )
    deck_id = create_res.json()["id"]
    res = client.post(f"/api/flashcards/decks/{deck_id}/refresh")
    data = res.json()
    assert data["name"] == "My Custom Deck"
    assert data["practice_mode"] == "recall"


def test_refresh_returns_404_for_missing_deck(client):
    res = client.post("/api/flashcards/decks/9999/refresh")
    assert res.status_code == 404


def test_refresh_deck_returns_deck_detail_with_cards(client, seeded_words):
    create_res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 3,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "not_practiced",
        },
    )
    deck_id = create_res.json()["id"]
    res = client.post(f"/api/flashcards/decks/{deck_id}/refresh")
    data = res.json()
    assert "cards" in data
    assert len(data["cards"]) > 0
