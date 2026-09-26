"""A stand-in for `ollama.Client` that records requests and replays a scripted reply."""

import json

CANNED_REPLY_CHUNKS = ("¡Hola! ", "¿Adónde ", "viaja?")
CANNED_JSON = json.dumps({"verdict": "correct", "corrections": []})


class ScriptedOllamaClient:
    """Answers `chat` like the Ollama client: chunks when streaming, one message otherwise."""

    def __init__(self, chunks=CANNED_REPLY_CHUNKS, error: Exception | None = None) -> None:
        self._chunks = tuple(chunks)
        self._error = error
        self.chat_calls: list[dict] = []
        self.generate_calls: list[dict] = []

    def chat(self, **kwargs):
        self.chat_calls.append(kwargs)
        if self._error is not None:
            raise self._error
        if kwargs.get("stream"):
            return iter([{"message": {"content": chunk}} for chunk in self._chunks])
        content = CANNED_JSON if "format" in kwargs else "".join(self._chunks)
        return {"message": {"content": content}}

    def generate(self, **kwargs):
        self.generate_calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return {"response": ""}

    def fail_with(self, error: Exception) -> None:
        """Make every later call raise, as a daemon that stopped mid-conversation would."""
        self._error = error
