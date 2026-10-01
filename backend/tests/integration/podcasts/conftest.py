"""Fixtures for the podcast integration tests. The harness lives in tests/support."""

import pytest

from tests.support.podcast_harness import podcast_harness


@pytest.fixture
def podcast_client(tmp_path):
    with podcast_harness(tmp_path) as harness:
        yield harness
