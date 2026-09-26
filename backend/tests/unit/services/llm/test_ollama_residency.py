"""T112: which local models a live conversation session is holding in memory (FR-S06, FR-S08)."""

from app.services.llm.ollama_residency import OllamaResidency

MODEL = "llama3.2"
OTHER_MODEL = "mistral"


def test_a_model_no_session_holds_keeps_ollamas_default():
    assert OllamaResidency(30).keep_alive_for(MODEL) is None


def test_a_held_model_keeps_the_session_keep_alive():
    residency = OllamaResidency(30)

    residency.hold(MODEL)

    assert residency.keep_alive_for(MODEL) == "30m"


def test_only_the_last_release_reports_the_model_free():
    residency = OllamaResidency(30)
    residency.hold(MODEL)
    residency.hold(MODEL)

    assert residency.release(MODEL) is False
    assert residency.keep_alive_for(MODEL) == "30m"
    assert residency.release(MODEL) is True
    assert residency.keep_alive_for(MODEL) is None


def test_holds_are_counted_per_model():
    residency = OllamaResidency(30)

    residency.hold(MODEL)

    assert residency.keep_alive_for(OTHER_MODEL) is None


def test_session_keep_alive_is_the_configured_duration():
    assert OllamaResidency(45).session_keep_alive == "45m"
