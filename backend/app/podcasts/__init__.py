"""Podcasts: shows, hosts and episodes (feature 007).

The package root is the only import surface for code outside the package (contracts §12),
except the composition root, `services/factory.py`. `router` is loaded on first use, so the
factory and the router can depend on each other's modules without an import cycle.
"""

from app.podcasts.catalog import PODCAST_SCENARIO_ID
from app.podcasts.services.speaker_views import PodcastMessageVoices

__all__ = ["router", "PODCAST_SCENARIO_ID", "PodcastMessageVoices"]


def __getattr__(name: str):
    if name == "router":
        from app.podcasts.routes import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
