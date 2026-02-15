"""API routes for runtime settings."""

from __future__ import annotations

from fastapi import APIRouter

from upscaler.api.schemas import SettingsSchema
from upscaler.core.config import settings

router = APIRouter(tags=["settings"])


@router.get("/settings")
async def get_settings() -> SettingsSchema:
    """Get current settings."""
    return SettingsSchema(
        tile_size=settings.tile_size,
        tile_overlap=settings.tile_overlap,
        default_format=settings.default_format,
        jpeg_quality=settings.jpeg_quality,
        fp16=settings.fp16,
        default_scale=settings.default_scale,
        max_loaded_models=settings.max_loaded_models,
    )


@router.put("/settings")
async def update_settings(new_settings: SettingsSchema) -> SettingsSchema:
    """Update runtime settings (does not persist to config.yaml)."""
    settings.tile_size = new_settings.tile_size
    settings.tile_overlap = new_settings.tile_overlap
    settings.default_format = new_settings.default_format
    settings.jpeg_quality = new_settings.jpeg_quality
    settings.fp16 = new_settings.fp16
    settings.default_scale = new_settings.default_scale
    settings.max_loaded_models = new_settings.max_loaded_models
    return new_settings
