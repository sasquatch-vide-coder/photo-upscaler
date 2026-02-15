"""API routes for multi-model comparison."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from upscaler.api.dependencies import get_comparison_runner, get_progress
from upscaler.api.schemas import ComparisonResponse, ComparisonResultSchema
from upscaler.core.config import settings

router = APIRouter(tags=["compare"])

# In-memory comparison results
_comparisons: dict[str, ComparisonResponse] = {}


@router.post("/compare")
async def compare_models(
    file: UploadFile = File(...),
    model_ids: str = Form(...),  # comma-separated
    scale: int = Form(4),
    output_format: str = Form("png"),
    tile_size: int = Form(0),
    jpeg_quality: int = Form(0),
):
    """Run comparison across multiple models. Returns comparison_id, results stream via WebSocket."""
    runner = get_comparison_runner()
    models_list = [m.strip() for m in model_ids.split(",") if m.strip()]

    if not models_list:
        raise HTTPException(status_code=400, detail="No models specified")

    # Save upload
    temp_dir = settings.temp_path
    temp_dir.mkdir(parents=True, exist_ok=True)
    comparison_id = uuid.uuid4().hex[:12]
    input_path = temp_dir / f"compare_{comparison_id}_{file.filename}"

    with open(input_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Save a copy as the "original" for the comparison view
    original_id = f"original_{comparison_id}"
    import shutil
    original_copy = temp_dir / f"{original_id}{input_path.suffix}"
    shutil.copy2(input_path, original_copy)

    # Output dir for this comparison
    output_dir = temp_dir / f"compare_{comparison_id}"
    output_dir.mkdir(exist_ok=True)

    _comparisons[comparison_id] = ComparisonResponse(
        comparison_id=comparison_id,
        input_image_id=original_id,
        scale=scale,
    )

    async def run_comparison():
        try:
            result = await asyncio.to_thread(
                runner.compare,
                input_path=input_path,
                model_ids=models_list,
                scale=scale,
                output_dir=output_dir,
                output_format=output_format,
                tile_size=tile_size if tile_size > 0 else None,
                jpeg_quality=jpeg_quality if jpeg_quality > 0 else None,
            )

            for r in result.results:
                # Use actual output filename stem as image_id so serving works
                if r.output_path:
                    image_id = Path(r.output_path).stem
                else:
                    image_id = f"compare_{comparison_id}_{r.model_id}"
                _comparisons[comparison_id].results.append(
                    ComparisonResultSchema(
                        model_id=r.model_id,
                        image_id=image_id,
                        duration_seconds=r.duration_seconds,
                        success=r.success,
                        error=r.error,
                    )
                )
        except Exception as e:
            _comparisons[comparison_id].results.append(
                ComparisonResultSchema(
                    model_id="error",
                    image_id="",
                    duration_seconds=0,
                    success=False,
                    error=str(e),
                )
            )

    asyncio.create_task(run_comparison())
    return {"comparison_id": comparison_id, "input_image_id": original_id}


@router.get("/compare/{comparison_id}")
async def get_comparison(comparison_id: str) -> ComparisonResponse:
    """Get comparison results (may be partial if still running)."""
    if comparison_id not in _comparisons:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return _comparisons[comparison_id]
