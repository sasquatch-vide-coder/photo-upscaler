"""API routes for model management."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from upscaler.api.dependencies import get_model_manager, get_progress
from upscaler.api.schemas import ModelInfoSchema, RegistryModelSchema, DownloadRequest
from upscaler.core.model_registry import (
    list_available,
    list_not_downloaded,
    download_model,
    get_entry,
)

router = APIRouter(tags=["models"])


@router.get("/models")
async def list_models() -> list[ModelInfoSchema]:
    """List all installed models with loaded status."""
    manager = get_model_manager()
    models = manager.list_models()
    return [
        ModelInfoSchema(
            model_id=m.model_id,
            filename=m.filename,
            architecture=m.architecture,
            scale=m.scale,
            file_size_mb=m.file_size_mb,
            is_loaded=manager.is_loaded(m.model_id),
        )
        for m in models
    ]


@router.get("/models/available")
async def list_available_models() -> list[RegistryModelSchema]:
    """List all downloadable models from the registry."""
    entries = list_available()
    not_dl = {e.key for e in list_not_downloaded()}
    return [
        RegistryModelSchema(
            key=e.key,
            name=e.name,
            architecture=e.architecture,
            scale=e.scale,
            is_downloaded=e.key not in not_dl,
        )
        for e in entries
    ]


@router.post("/models/download")
async def download_model_route(req: DownloadRequest) -> dict:
    """Download a model from the registry."""
    entry = get_entry(req.model_key)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Unknown model key: {req.model_key}")

    progress = get_progress()
    manager = get_model_manager()

    await asyncio.to_thread(download_model, req.model_key, progress=progress)

    # Re-scan to pick up the new model
    await asyncio.to_thread(manager.scan)

    return {"status": "ok", "model_key": req.model_key}
