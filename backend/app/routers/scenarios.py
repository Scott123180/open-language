from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services.factory import get_scenario_provider
from app.services.scenario.base import Scenario, ScenarioProvider

router = APIRouter(tags=["scenarios"])


class ScenarioResponse(BaseModel):
    id: str
    title: str
    description: str


def _to_response(s: Scenario) -> ScenarioResponse:
    return ScenarioResponse(id=s.id, title=s.title, description=s.description)


@router.get("/scenarios/current", response_model=ScenarioResponse)
def get_current_scenario(provider: ScenarioProvider = Depends(get_scenario_provider)):
    return _to_response(provider.get_random())


@router.get("/scenarios/next", response_model=ScenarioResponse)
def get_next_scenario(
    exclude_id: str | None = None,
    provider: ScenarioProvider = Depends(get_scenario_provider),
):
    return _to_response(provider.get_random(exclude_id=exclude_id))
