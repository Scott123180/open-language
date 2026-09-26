"""T065: the availability contract every provider's checker meets."""

from app.services.llm.availability import AlwaysAvailable, ProviderAvailability


def test_always_available_reports_available_with_nothing_to_explain():
    assert AlwaysAvailable().check() == ProviderAvailability(
        is_available=True, reason=None, message=None
    )
