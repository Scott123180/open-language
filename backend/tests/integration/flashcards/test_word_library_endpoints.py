"""Integration tests for word library API endpoints (T014 / T066).

T014 covers:
  GET  /api/flashcards/words
  PATCH /api/flashcards/words/{id}/classification
  DELETE /api/flashcards/words/{id}

T066 extends with:
  GET /api/flashcards/words/{id}/info/{cache_type}
"""

from datetime import UTC, datetime

import pytest

from app.models.vocabulary_item import VocabularyItem


@pytest.fixture()
def word(db_session):
    item = VocabularyItem(
        word="bonjour",
        translation="hello",
        target_language="fr",
        native_language="en",
        saved_at=datetime.now(UTC),
        classification="not_practiced",
        manual_override=False,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture()
def three_words(db_session):
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
        VocabularyItem(
            word="oui",
            translation="yes",
            target_language="fr",
            native_language="en",
            saved_at=datetime.now(UTC),
            classification="learned",
            manual_override=False,
        ),
    ]
    db_session.add_all(words)
    db_session.commit()
    for w in words:
        db_session.refresh(w)
    return words


class TestGetWords:
    def test_returns_empty_list_when_no_words(self, client):
        response = client.get("/api/flashcards/words")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_all_words(self, client, three_words):
        response = client.get("/api/flashcards/words")
        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_filter_by_single_classification(self, client, three_words):
        response = client.get("/api/flashcards/words?classification=difficult")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["classification"] == "difficult"

    def test_filter_by_multiple_classifications(self, client, three_words):
        response = client.get(
            "/api/flashcards/words?classification=difficult&classification=learned"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_filter_by_search(self, client, three_words):
        response = client.get("/api/flashcards/words?search=merci")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["word"] == "merci"

    def test_word_item_has_required_fields(self, client, word):
        response = client.get("/api/flashcards/words")
        assert response.status_code == 200
        item = response.json()[0]
        assert "id" in item
        assert "word" in item
        assert "translation" in item
        assert "classification" in item
        assert "manual_override" in item
        assert "saved_at" in item


class TestPatchClassification:
    def test_updates_classification(self, client, word):
        response = client.patch(
            f"/api/flashcards/words/{word.id}/classification",
            json={"classification": "difficult"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["classification"] == "difficult"
        assert data["manual_override"] is True

    def test_returns_404_for_missing_word(self, client):
        response = client.patch(
            "/api/flashcards/words/9999/classification",
            json={"classification": "difficult"},
        )
        assert response.status_code == 404

    def test_rejects_invalid_classification(self, client, word):
        response = client.patch(
            f"/api/flashcards/words/{word.id}/classification",
            json={"classification": "invalid_value"},
        )
        assert response.status_code == 422


class TestDeleteWord:
    def test_deletes_word(self, client, word):
        response = client.delete(f"/api/flashcards/words/{word.id}")
        assert response.status_code == 204

        list_response = client.get("/api/flashcards/words")
        assert list_response.json() == []

    def test_returns_404_for_missing_word(self, client):
        response = client.delete("/api/flashcards/words/9999")
        assert response.status_code == 404


class TestBulkDeleteWords:
    def test_deletes_multiple_words(self, client, three_words):
        ids = [three_words[0].id, three_words[1].id]
        response = client.request("DELETE", "/api/flashcards/words", json={"ids": ids})
        assert response.status_code == 200
        assert response.json()["deleted"] == 2

        list_response = client.get("/api/flashcards/words")
        remaining = list_response.json()
        assert len(remaining) == 1
        assert remaining[0]["word"] == "oui"

    def test_returns_zero_deleted_for_missing_ids(self, client):
        response = client.request("DELETE", "/api/flashcards/words", json={"ids": [9998, 9999]})
        assert response.status_code == 200
        assert response.json()["deleted"] == 0

    def test_rejects_empty_ids_list(self, client):
        response = client.request("DELETE", "/api/flashcards/words", json={"ids": []})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# T066 — GET /api/flashcards/words/{id}/info/{cache_type}
# ---------------------------------------------------------------------------


class TestWordInfoEndpoint:
    def test_returns_cached_content_on_cache_hit(self, client, word, db_session):
        from datetime import UTC, datetime

        from app.flashcards.models import WordLlmCache

        cached = WordLlmCache(
            vocabulary_item_id=word.id,
            cache_type="meanings",
            content="Bonjour: a greeting in French.",
            language="fr",
            generated_at=datetime.now(UTC),
        )
        db_session.add(cached)
        db_session.commit()

        res = client.get(f"/api/flashcards/words/{word.id}/info/meanings")
        assert res.status_code == 200
        assert res.json()["content"] == "Bonjour: a greeting in French."

    def test_returns_404_for_missing_word(self, client):
        res = client.get("/api/flashcards/words/9999/info/meanings")
        assert res.status_code == 404

    def test_returns_503_when_llm_unavailable_and_no_cache(self, client, word):
        """No cached content and no LLM configured → 503."""
        res = client.get(f"/api/flashcards/words/{word.id}/info/meanings")
        assert res.status_code == 503

    def test_cache_type_is_respected(self, client, word, db_session):
        from datetime import UTC, datetime

        from app.flashcards.models import WordLlmCache

        usage_cache = WordLlmCache(
            vocabulary_item_id=word.id,
            cache_type="usage",
            content="Je dis bonjour chaque matin.",
            language="fr",
            generated_at=datetime.now(UTC),
        )
        db_session.add(usage_cache)
        db_session.commit()

        res = client.get(f"/api/flashcards/words/{word.id}/info/usage")
        assert res.status_code == 200
        assert "bonjour" in res.json()["content"]
