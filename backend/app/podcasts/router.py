"""/api/podcasts: shows, preferences and episodes (contracts §1–§8)."""

import random

from fastapi import APIRouter

from app.podcasts.services.turn_policy import TurnPolicy

router = APIRouter(prefix="/api/podcasts", tags=["podcasts"])


def get_turn_policy() -> TurnPolicy:
    """A policy drawing from fresh randomness per request; tests inject a seeded one."""
    return TurnPolicy(random.Random())
