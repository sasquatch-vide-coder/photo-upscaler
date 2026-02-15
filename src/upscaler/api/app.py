"""FastAPI application factory with lifespan management."""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from upscaler.core.config import settings
from upscaler.api.dependencies import init_dependencies, cleanup_dependencies, get_progress
from upscaler.api.websocket import (
    router as ws_router,
    broadcast_worker,
    progress_to_ws_callback,
)
from upscaler.api.routes import models, upscale, compare, images, settings as settings_route

logger = logging.getLogger(__name__)


async def _temp_cleanup_loop():
    """Periodically clean up old temp files."""
    while True:
        await asyncio.sleep(300)  # Check every 5 minutes
        temp_dir = settings.temp_path
        if not temp_dir.exists():
            continue
        cutoff = time.time() - (settings.temp_max_age_minutes * 60)
        for f in temp_dir.iterdir():
            if f.is_file() and f.stat().st_mtime < cutoff:
                try:
                    f.unlink()
                except OSError:
                    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Startup
    init_dependencies()
    progress = get_progress()
    progress.add_callback(progress_to_ws_callback)

    # Ensure temp dir exists
    settings.temp_path.mkdir(parents=True, exist_ok=True)
    settings.output_path.mkdir(parents=True, exist_ok=True)

    # Start background tasks
    broadcast_task = asyncio.create_task(broadcast_worker())
    cleanup_task = asyncio.create_task(_temp_cleanup_loop())

    logger.info("Server started. Models dir: %s", settings.models_path)
    yield

    # Shutdown
    broadcast_task.cancel()
    cleanup_task.cancel()
    cleanup_dependencies()

    # Clean temp dir
    temp_dir = settings.temp_path
    if temp_dir.exists():
        for f in temp_dir.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                except OSError:
                    pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Photo Upscaler",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(ws_router)
    app.include_router(models.router, prefix="/api")
    app.include_router(upscale.router, prefix="/api")
    app.include_router(compare.router, prefix="/api")
    app.include_router(images.router, prefix="/api")
    app.include_router(settings_route.router, prefix="/api")

    # Serve web UI static files
    web_dir = Path(__file__).parent.parent / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")

    return app
