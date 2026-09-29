"""Conversation summary: a short, grounded account of a conversation so far (feature 007, US6).

The package root is the only import surface outside the package, except the composition root,
`services/factory.py`. `router` is loaded on first use, so the factory and the router can depend
on each other's modules without an import cycle.
"""

from app.conversation_summary.services.speaker_names import SpeakerNames

__all__ = ["router", "SpeakerNames"]


def __getattr__(name: str):
    if name == "router":
        from app.conversation_summary.routes import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
