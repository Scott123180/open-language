"""Named thresholds for correction policy (research.md summary of constants).

Every value here is a policy decision, not a tuning knob discovered at runtime.
The two thresholds that a host may reasonably want to change —
``low_confidence_threshold`` and ``correction_timeout_seconds`` — live on
``app.config.Settings`` instead, so they can be overridden by environment.
"""

# FR-008: at most two corrections surface for one learner message.
MAX_CORRECTIONS_PER_MESSAGE = 2

# FR-018: after two consecutive corrected attempts the next message is answered
# whatever it contains, so a learner can never be trapped in a correction loop.
MAX_CONSECUTIVE_CORRECTED_ATTEMPTS = 2

# Fragmentary input ("sí", "gracias") carries no grammar worth evaluating.
MIN_WORDS_FOR_EVALUATION = 2

# FR-027: a bad microphone earns one "say that again", never a second.
MAX_REPEAT_REQUESTS_PER_MESSAGE = 1
