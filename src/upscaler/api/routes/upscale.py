"""API routes for single and batch upscaling."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from upscaler.api.dependencies import get_engine, get_model_manager, get_progress
from upscaler.api.schemas import JobStatusResponse
from upscaler.core.config import settings
from upscaler.core.batch import run_batch

router = APIRouter(tags=["upscale"])

# In-memory job tracking for batch operations
_jobs: dict[str, JobStatusResponse] = {}


@router.post("/upscale")
async def upscale_image(
    file: UploadFile = File(...),
    model_id: str = Form(...),
    scale: int = Form(4),
    output_format: str = Form("png"),
    tile_size: int = Form(0),
    jpeg_quality: int = Form(0),
):
    """Upscale a single image. Returns the processed image file."""
    engine = get_engine()

    # Save upload to temp
    temp_dir = settings.temp_path
    temp_dir.mkdir(parents=True, exist_ok=True)
    upload_id = uuid.uuid4().hex[:12]
    input_path = temp_dir / f"upload_{upload_id}_{file.filename}"

    with open(input_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Build output path in temp
    fmt_ext = {"png": ".png", "jpg": ".jpg", "jpeg": ".jpg", "webp": ".webp"}.get(output_format.lower(), ".png")
    output_path = temp_dir / f"result_{upload_id}_{scale}x_{model_id}{fmt_ext}"

    try:
        result_path = await asyncio.to_thread(
            engine.upscale,
            input_path=input_path,
            output_path=output_path,
            model_id=model_id,
            scale=scale,
            output_format=output_format,
            tile_size=tile_size if tile_size > 0 else None,
            jpeg_quality=jpeg_quality if jpeg_quality > 0 else None,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(fmt_ext, "image/png")

    return FileResponse(str(result_path), media_type=media_type, filename=result_path.name)


@router.post("/upscale/batch")
async def upscale_batch(
    input_dir: str = Form(...),
    output_dir: str = Form(""),
    model_id: str = Form(...),
    scale: int = Form(4),
    output_format: str = Form("png"),
    recursive: bool = Form(False),
    skip_existing: bool = Form(False),
):
    """Start a batch upscaling job. Returns a job_id for tracking."""
    engine = get_engine()
    progress = get_progress()
    job_id = uuid.uuid4().hex[:12]

    _jobs[job_id] = JobStatusResponse(job_id=job_id, status="pending")

    async def run_job():
        _jobs[job_id].status = "running"
        try:
            result = await asyncio.to_thread(
                run_batch,
                engine=engine,
                input_dir=input_dir,
                output_dir=output_dir or None,
                model_id=model_id,
                scale=scale,
                output_format=output_format,
                recursive=recursive,
                skip_existing=skip_existing,
                progress=progress,
            )
            _jobs[job_id].status = "completed"
            _jobs[job_id].progress = 1.0
            _jobs[job_id].results = [
                {"completed": result.completed, "skipped": result.skipped, "failed": result.failed}
            ]
        except Exception as e:
            _jobs[job_id].status = "failed"
            _jobs[job_id].error = str(e)

    asyncio.create_task(run_job())
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Check status of a batch job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]
