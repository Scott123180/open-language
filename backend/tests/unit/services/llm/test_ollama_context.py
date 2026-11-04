"""011 R18: a small local model gets a larger context window than Ollama's default."""

import pytest

from app.services.llm.ollama_context import ContextPolicy, OllamaContextWindow

GIGABYTE = 1_000_000_000
POLICY = ContextPolicy(small_model_max_bytes=10 * GIGABYTE, small_model_context_tokens=8192)


class ListingClient:
    """Answers `list()` like the Ollama client, counting the calls."""

    def __init__(self, sizes: dict[str, int], error: Exception | None = None) -> None:
        self._sizes = sizes
        self._error = error
        self.list_calls = 0

    def list(self):
        self.list_calls += 1
        if self._error is not None:
            raise self._error
        return {"models": [{"model": name, "size": size} for name, size in self._sizes.items()]}


SIZES = {"llama3.1:8b": 5 * GIGABYTE, "qwen3.6:latest": 24 * GIGABYTE, "mistral:latest": GIGABYTE}


@pytest.fixture()
def window() -> OllamaContextWindow:
    return OllamaContextWindow(POLICY)


def test_a_small_model_asks_for_the_larger_window(window):
    assert window.options_for(ListingClient(SIZES), "llama3.1:8b") == {"num_ctx": 8192}


def test_a_large_model_keeps_ollamas_default(window):
    assert window.options_for(ListingClient(SIZES), "qwen3.6:latest") is None


def test_a_model_named_without_a_tag_is_its_latest_tag(window):
    assert window.options_for(ListingClient(SIZES), "mistral") == {"num_ctx": 8192}


def test_a_model_ollama_does_not_list_keeps_ollamas_default(window):
    assert window.options_for(ListingClient(SIZES), "phi3:mini") is None


def test_each_model_is_looked_up_once_so_every_request_asks_for_the_same_window(window):
    client = ListingClient(SIZES)

    window.options_for(client, "llama3.1:8b")
    window.options_for(client, "llama3.1:8b")

    assert client.list_calls == 1


def test_an_unreachable_ollama_keeps_the_default_and_asks_again_next_time(window):
    window.options_for(ListingClient(SIZES, error=ConnectionError("refused")), "llama3.1:8b")

    assert window.options_for(ListingClient(SIZES), "llama3.1:8b") == {"num_ctx": 8192}


def test_a_policy_needs_a_positive_window():
    with pytest.raises(ValueError, match="context"):
        ContextPolicy(small_model_max_bytes=GIGABYTE, small_model_context_tokens=0)
