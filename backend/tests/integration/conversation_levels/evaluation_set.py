"""The fixed evaluation set for the level benchmark: 4 scenarios × 5 learner turns (research R9).

Each turn may be tagged with the requirement it probes, so the review sheet can ask the matching
question about the reply.
"""

from dataclasses import dataclass

FR_012 = "FR-012"  # a scenario that needs a few specialist words
FR_013 = "FR-013"  # the learner writes well above the level
FR_014 = "FR-014"  # the learner asks for simpler speech

REVIEW_QUESTIONS = {
    FR_012: "FR-012: were above-level words only essential topic words?",
    FR_013: "FR-013: did it answer the substance while staying at the level?",
    FR_014: "FR-014: was it simpler than the previous reply?",
}


@dataclass(frozen=True, slots=True)
class LearnerTurn:
    text: str
    probes: str | None = None


@dataclass(frozen=True, slots=True)
class ScriptedConversation:
    scenario_id: str
    turns: tuple[LearnerTurn, ...]


EVALUATION_SET: tuple[ScriptedConversation, ...] = (
    ScriptedConversation(
        "order-at-restaurant",
        (
            LearnerTurn("Hola, buenas tardes."),
            LearnerTurn("Quiero ver el menú, por favor."),
            LearnerTurn(
                "Aunque normalmente preferiría algo ligero, si me recomendara el plato del día, "
                "lo pediría sin dudarlo.",
                FR_013,
            ),
            LearnerTurn("Más despacio, por favor, no entiendo.", FR_014),
            LearnerTurn("Un agua, por favor. Gracias."),
        ),
    ),
    ScriptedConversation(
        "buy-train-ticket",
        (
            LearnerTurn("Hola. Quiero un billete a Madrid."),
            LearnerTurn("Para mañana por la mañana."),
            LearnerTurn("¿Cuánto cuesta?"),
            LearnerTurn("¿Hay un tren más temprano?"),
            LearnerTurn("Vale, gracias. Adiós."),
        ),
    ),
    ScriptedConversation(
        "call-doctors-office",
        (
            LearnerTurn("Hola, necesito una cita con el médico.", FR_012),
            LearnerTurn("Me duele la garganta y tengo fiebre.", FR_012),
            LearnerTurn("¿Necesito una receta?", FR_012),
            LearnerTurn("No entiendo. ¿Puede hablar más despacio?", FR_014),
            LearnerTurn("El jueves está bien. Gracias."),
        ),
    ),
    ScriptedConversation(
        "check-into-hotel",
        (
            LearnerTurn("Buenas noches. Tengo una reserva."),
            LearnerTurn("Me llamo Ana García."),
            LearnerTurn(
                "Si hubiera sabido que el vuelo llegaría tan tarde, habría reservado una "
                "habitación más cerca del aeropuerto.",
                FR_013,
            ),
            LearnerTurn("¿A qué hora es el desayuno?"),
            LearnerTurn("Perfecto. Muchas gracias."),
        ),
    ),
)
