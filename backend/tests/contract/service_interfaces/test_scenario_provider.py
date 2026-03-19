import pytest
from app.services.scenario.base import Scenario, ScenarioProvider
from app.services.scenario.static import StaticScenarioProvider


@pytest.fixture
def provider() -> ScenarioProvider:
    return StaticScenarioProvider()


def test_get_all_returns_nonempty_list(provider: ScenarioProvider) -> None:
    scenarios = provider.get_all()
    assert isinstance(scenarios, list)
    assert len(scenarios) >= 1
    assert all(isinstance(s, Scenario) for s in scenarios)


def test_get_random_returns_scenario(provider: ScenarioProvider) -> None:
    result = provider.get_random()
    assert isinstance(result, Scenario)
    assert result.id
    assert result.title


def test_get_random_exclude_id_never_returns_excluded(provider: ScenarioProvider) -> None:
    all_scenarios = provider.get_all()
    for scenario in all_scenarios:
        # Only skip if there's more than one scenario to choose from
        if len(all_scenarios) <= 1:
            continue
        results = {provider.get_random(exclude_id=scenario.id).id for _ in range(20)}
        assert scenario.id not in results, (
            f"get_random() returned excluded id '{scenario.id}'"
        )


def test_get_random_no_consecutive_repeats(provider: ScenarioProvider) -> None:
    all_scenarios = provider.get_all()
    if len(all_scenarios) <= 1:
        pytest.skip("Need at least 2 scenarios for this test")
    previous = provider.get_random()
    for _ in range(10):
        current = provider.get_random()
        assert current.id != previous.id
        previous = current
