"""Shared application state, injected into routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from .bus import EventBus
from .jobs import JobRunner
from .settings import Settings
from .storage import Database


@dataclass(frozen=True)
class AppState:
    settings: Settings
    database: Database
    bus: EventBus
    runner: JobRunner


def get_state(request: Request) -> AppState:
    return request.app.state.services


StateDep = Annotated[AppState, Depends(get_state)]
"""Injected application state. `Annotated` keeps FastAPI's dependency calls
out of argument defaults, which is both the modern idiom and lint-clean."""
