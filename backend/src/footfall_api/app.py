"""FastAPI application factory."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .bus import EventBus
from .dependencies import AppState
from .jobs import JobRunner
from .routes import jobs as jobs_routes
from .routes import videos as videos_routes
from .settings import Settings
from .storage import Database

FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


def create_app(settings: Settings | None = None, *, tracker_factory=None) -> FastAPI:
    resolved = settings or Settings.from_env()
    resolved.ensure_directories()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Worker threads publish through this loop; it only exists once the
        # app is actually running.
        app.state.services.bus.bind_loop(asyncio.get_running_loop())
        try:
            yield
        finally:
            app.state.services.runner.shutdown()

    app = FastAPI(title="Footfall", version="0.3.0", lifespan=lifespan)

    database = Database(resolved.database_path)
    bus = EventBus()
    app.state.services = AppState(
        settings=resolved,
        database=database,
        bus=bus,
        runner=JobRunner(
            database,
            bus,
            max_workers=resolved.max_concurrent_jobs,
            preview_width=resolved.preview_width,
            tracker_factory=tracker_factory,
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.allowed_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(videos_routes.router)
    app.include_router(jobs_routes.router)

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "max_concurrent_jobs": resolved.max_concurrent_jobs}

    # Serving the built dashboard is optional: during development Vite serves
    # it, and the API is reached cross-origin.
    if FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="dashboard")

    return app
