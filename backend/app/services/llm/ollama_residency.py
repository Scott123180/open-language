"""Which local models a live conversation session is holding in memory (FR-S06, FR-S08).

Ollama resets a model's unload timer on every request to that request's `keep_alive`. While a
conversation session is live, every request for its model therefore carries the session
keep-alive, or a learning-tool lookup would drop the model back to the five-minute default and
stall the next turn. Once the model's last session closes, requests leave `keep_alive` unset
again, so Ollama's own policy applies.
"""

import threading
from collections import Counter


class OllamaResidency:
    """Counts live Ollama conversation sessions per model. One per process, shared by the
    providers the registry builds for each request."""

    def __init__(self, session_keep_alive_minutes: int) -> None:
        self._session_keep_alive = f"{session_keep_alive_minutes}m"
        self._live_sessions: Counter[str] = Counter()
        self._lock = threading.Lock()

    @property
    def session_keep_alive(self) -> str:
        return self._session_keep_alive

    def keep_alive_for(self, model: str) -> str | None:
        """The keep-alive a request for `model` carries; None leaves Ollama's default."""
        with self._lock:
            is_held = self._live_sessions[model] > 0
        return self._session_keep_alive if is_held else None

    def hold(self, model: str) -> None:
        with self._lock:
            self._live_sessions[model] += 1

    def release(self, model: str) -> bool:
        """Drop one session's hold. True when it was the model's last."""
        with self._lock:
            self._live_sessions[model] -= 1
            if self._live_sessions[model] > 0:
                return False
            del self._live_sessions[model]
            return True
