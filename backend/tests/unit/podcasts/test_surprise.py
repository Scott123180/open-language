"""T104: Surprise me leans on the learner's interests and does not repeat itself (FR-022, FR-023)."""

import itertools
import random

from app.podcasts.services.surprise import (
    SURPRISE_ANGLES,
    SURPRISE_HISTORY_SIZE,
    SURPRISE_TOPICS,
    RecentSurprises,
    SurpriseIdea,
    SurpriseTopics,
)

INTERESTS = ("football", "cooking")
DRAWS = 300


def _draws(interests: tuple[str, ...], count: int = DRAWS, seed: int = 11) -> list[SurpriseIdea]:
    topics = SurpriseTopics(random.Random(seed))
    return [topics.draw(interests) for _ in range(count)]


def test_there_are_forty_topics_and_twelve_angles():
    assert len(set(SURPRISE_TOPICS)) == 40
    assert len(set(SURPRISE_ANGLES)) == 12


def test_with_interests_most_draws_take_an_interest_as_the_topic():
    from_interests = sum(draw.topic in INTERESTS for draw in _draws(INTERESTS))

    assert from_interests / DRAWS >= 0.6


def test_with_interests_some_draws_still_take_a_built_in_topic():
    assert any(draw.topic in SURPRISE_TOPICS for draw in _draws(INTERESTS))


def test_without_interests_every_topic_is_built_in():
    assert all(draw.topic in SURPRISE_TOPICS for draw in _draws(()))


def test_every_angle_is_built_in():
    assert all(draw.angle in SURPRISE_ANGLES for draw in _draws(INTERESTS))


def test_the_idea_reads_as_the_angle_then_the_topic():
    idea = SurpriseIdea(topic="football", angle="a friendly debate about")

    assert idea.idea == "a friendly debate about football"


def test_the_last_ten_pairs_are_never_repeated():
    topics, recent = SurpriseTopics(random.Random(5)), RecentSurprises()
    picked = [recent.fresh(lambda: topics.draw(("football",))) for _ in range(DRAWS)]

    for index, idea in enumerate(picked):
        assert idea not in picked[max(0, index - SURPRISE_HISTORY_SIZE) : index]


def test_a_repeat_is_redrawn_until_it_is_fresh():
    recent = RecentSurprises()
    same, other = SurpriseIdea("football", SURPRISE_ANGLES[0]), SurpriseIdea("chess", "x")
    draws = itertools.chain([same, same, same], itertools.repeat(other))
    recent.fresh(lambda: same)

    assert recent.fresh(lambda: next(draws)) == other


def test_a_draw_that_never_freshens_falls_back_to_an_unused_built_in_pair():
    recent = RecentSurprises()
    same = SurpriseIdea("football", SURPRISE_ANGLES[0])
    recent.fresh(lambda: same)

    fallback = recent.fresh(lambda: same)

    assert fallback != same
    assert fallback.topic in SURPRISE_TOPICS
    assert fallback.angle in SURPRISE_ANGLES


def test_twenty_presses_give_at_least_fifteen_different_topic_and_angle_pairs():
    topics, recent = SurpriseTopics(random.Random(8)), RecentSurprises()

    picked = {recent.fresh(lambda: topics.draw(INTERESTS)) for _ in range(20)}

    assert len(picked) >= 15
