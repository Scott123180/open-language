"""T020: one line at a time per episode (research R12)."""

import pytest

from app.podcasts.services.episode_lock import EpisodeLocks


def test_a_free_episode_can_be_acquired():
    assert EpisodeLocks().try_acquire(57) is not None


def test_a_held_episode_cannot_be_acquired_again():
    locks = EpisodeLocks()
    held = locks.try_acquire(57)

    assert held is not None
    assert locks.try_acquire(57) is None


def test_releasing_frees_the_episode():
    locks = EpisodeLocks()

    with locks.try_acquire(57):
        pass

    assert locks.try_acquire(57) is not None


def test_different_episodes_do_not_block_each_other():
    locks = EpisodeLocks()
    locks.try_acquire(57)

    assert locks.try_acquire(58) is not None


def test_the_lock_is_released_when_the_guarded_block_raises():
    locks = EpisodeLocks()

    with pytest.raises(RuntimeError), locks.try_acquire(57):
        raise RuntimeError("the line failed")

    assert locks.try_acquire(57) is not None


def test_an_episode_reports_whether_a_line_is_in_progress():
    locks = EpisodeLocks()

    with locks.try_acquire(57):
        assert locks.is_held(57) is True

    assert locks.is_held(57) is False
