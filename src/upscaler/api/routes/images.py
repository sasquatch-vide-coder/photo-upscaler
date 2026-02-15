"""API routes for serving result images."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from upscaler.core.config import settings

router = APIRouter(tags=["images"])


@router.get("/images/{image_id}")
async def get_image(image_id: str):
    """Serve a result image from the temp directory."""
    temp_dir = settings.temp_path

    # Search temp dir (and subdirs) for a file matching the image_id prefix
    for path in temp_dir.rglob("*"):
        if path.is_file() and path.stem.startswith(image_id):
            media_type = _guess_media_type(path.suffix)
            return FileResponse(str(path), media_type=media_type)

    raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")


def _guess_media_type(ext: str) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }.get(ext.lower(), "application/octet-stream")
