"""Integration tests for GET /api/flashcards/analytics (T086)."""

from datetime import UTC, datetime

import pytest

from app.models.vocabulary_item import VocabularyItem


@pytest.fixture()
def seeded_vocab(db_session):
    words = [
        VocabularyItem(
            word="gato",
            translation="cat",
            target_language="es",
            native_language="en",
            saved_at=datetime.now(UTC),
            classification="not_practiced",
            manual_override=False,
        ),
        VocabularyItem(
            word="perro",
            translation="dog",
            target_language="es",
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


def test_analytics_returns_200(client, seeded_vocab):
    res = client.get("/api/flashcards/analytics?range=7d")
    assert res.status_code == 200


def test_analytics_response_has_required_keys(client, seeded_vocab):
    res = client.get("/api/flashcards/analytics?range=7d")
    data = res.json()
    assert "at_a_glance" in data
    assert "accuracy_trend" in data
    assert "daily_activity" in data
    assert "classification_over_time" in data
    assert "classification_now" in data
    assert "hardest_words" in data
    assert "recently_learned" in data
    assert "mode_performance" in data


def test_at_a_glance_reflects_word_count(client, seeded_vocab):
    res = client.get("/api/flashcards/analytics?range=all")
    data = res.json()
    assert data["at_a_glance"]["total_words"] == 2


def test_classification_now_counts_correct(client, seeded_vocab):
    res = client.get("/api/flashcards/analytics?range=7d")
    data = res.json()
    cn = data["classification_now"]
    assert cn["not_practiced"] == 1
    assert cn["difficult"] == 1


def test_analytics_range_7d(client, seeded_vocab):
    res = client.get("/api/flashcards/analytics?range=7d")
    assert res.status_code == 200


def test_analytics_range_30d(client, seeded_vocab):
    res = client.get("/api/flashcards/analytics?range=30d")
    assert res.status_code == 200


def test_analytics_range_all(client, seeded_vocab):
    res = client.get("/api/flashcards/analytics?range=all")
    assert res.status_code == 200


def test_analytics_accuracy_trend_from_sessions(client, seeded_vocab):
    """After a session, accuracy_trend should contain an entry."""
    deck_res = client.post(
        "/api/flashcards/decks",
        json={
            "size": 2,
            "word_source": "all",
            "practice_mode": "recall",
            "algorithm": "mixed_review",
        },
    )
    deck_id = deck_res.json()["id"]
    session_res = client.post("/api/flashcards/sessions", json={"deck_id": deck_id})
    session_id = session_res.json()["id"]
    client.post(
        f"/api/flashcards/sessions/{session_id}/cards/0",
        json={"rating": "knew_it", "response_type": None, "user_response": None},
    )
    client.post(f"/api/flashcards/sessions/{session_id}/end", json={"completed": True})

    res = client.get("/api/flashcards/analytics?range=7d")
    data = res.json()
    assert len(data["accuracy_trend"]) >= 1
    assert data["accuracy_trend"][0]["accuracy"] >= 0.0
