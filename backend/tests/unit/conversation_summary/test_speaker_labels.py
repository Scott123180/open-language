"""T078: transcript labels (FR-037)."""

from app.conversation_summary.services.summariser import SummaryLine, label_transcript


def _lines():
    return (SummaryLine(1, "assistant", "¡Hola!"), SummaryLine(2, "user", "Buenas."))


def test_a_roleplay_is_labelled_learner_and_partner():
    assert label_transcript(_lines(), None) == "Partner: ¡Hola!\nLearner: Buenas."


def test_an_episode_uses_the_hosts_names_and_the_learner_label():
    assert label_transcript(_lines(), {1: "Lucía", 2: "Sam"}) == "Lucía: ¡Hola!\nSam: Buenas."


def test_a_line_missing_from_the_map_falls_back_to_its_role():
    assert label_transcript(_lines(), {1: "Lucía"}) == "Lucía: ¡Hola!\nLearner: Buenas."
