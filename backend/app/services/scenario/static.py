import random

from app.services.scenario.base import Scenario, ScenarioProvider

_SCENARIOS: list[Scenario] = [
    Scenario(
        id="buy-train-ticket",
        title="Buy a Train Ticket",
        description="Purchase a train ticket at a station ticket counter.",
        ai_context_prompt="You are a ticket agent at a train station. Help the customer buy tickets.",
    ),
    Scenario(
        id="check-into-hotel",
        title="Check Into a Hotel",
        description="Check in at a hotel front desk after arriving.",
        ai_context_prompt="You are a hotel receptionist. Assist the guest with check-in.",
    ),
    Scenario(
        id="order-at-restaurant",
        title="Order at a Restaurant",
        description="Order food and drinks at a local restaurant.",
        ai_context_prompt="You are a waiter at a restaurant. Take the customer's order.",
    ),
    Scenario(
        id="call-doctors-office",
        title="Call a Doctor's Office",
        description="Schedule an appointment or ask about symptoms by phone.",
        ai_context_prompt="You are a receptionist at a medical clinic. Help the caller schedule an appointment.",
    ),
    Scenario(
        id="ask-for-directions",
        title="Ask for Directions",
        description="Ask a passerby for directions to a landmark.",
        ai_context_prompt="You are a local resident. Give directions to the requested place.",
    ),
    Scenario(
        id="job-interview",
        title="Job Interview",
        description="Participate in a job interview for an office position.",
        ai_context_prompt="You are a hiring manager conducting a job interview. Ask questions and respond to answers.",
    ),
    Scenario(
        id="rent-a-car",
        title="Rent a Car",
        description="Rent a vehicle at a car rental counter.",
        ai_context_prompt="You are a car rental agent. Help the customer rent a vehicle.",
    ),
    Scenario(
        id="visit-pharmacy",
        title="Visit a Pharmacy",
        description="Ask the pharmacist about medication or a prescription.",
        ai_context_prompt="You are a pharmacist. Assist the customer with their medication needs.",
    ),
    Scenario(
        id="report-lost-item",
        title="Report a Lost Item",
        description="Report a lost belonging at a lost-and-found desk.",
        ai_context_prompt="You are a lost-and-found clerk. Help the customer file a report for their missing item.",
    ),
    Scenario(
        id="board-airplane",
        title="Board an Airplane",
        description="Navigate the boarding process at an airport gate.",
        ai_context_prompt="You are a gate agent at an airport. Assist the passenger with boarding.",
    ),
]


class StaticScenarioProvider(ScenarioProvider):
    def __init__(self) -> None:
        self._last_id: str | None = None

    def get_all(self) -> list[Scenario]:
        return list(_SCENARIOS)

    def get_random(self, exclude_id: str | None = None) -> Scenario:
        effective_exclude = exclude_id if exclude_id is not None else self._last_id
        candidates = [s for s in _SCENARIOS if s.id != effective_exclude]
        if not candidates:
            candidates = list(_SCENARIOS)
        chosen = random.choice(candidates)
        self._last_id = chosen.id
        return chosen
