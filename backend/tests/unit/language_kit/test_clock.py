"""The system clock tells the time zone-aware, in UTC."""

from datetime import UTC

from language_kit.clock import SystemClock


def test_the_system_clock_is_utc():
    assert SystemClock().now().tzinfo is UTC
