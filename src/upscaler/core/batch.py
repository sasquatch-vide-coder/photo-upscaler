"""Batch processing — upscale all images in a directory."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from upscaler.core.config import settings
from upscaler.core.image_io import SUPPORTED_EXTENSIONS
from upscaler.core.progress import EventType, ProgressReporter
from upscaler.core.upscale_engine import UpscaleEngine

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    total: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    outputs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def find_images(input_dir: Path, recursive: bool = False) -> list[Path]:
    """Find all supported image files in a directory."""
    pattern = "**/*" if recursive else "*"
    files = []
    for path in input_dir.glob(pattern):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
    return sorted(files)


def run_batch(
    engine: UpscaleEngine,
    input_dir: str | Path,
    output_dir: str | Path | None = None,
    model_id: str | None = None,
    scale: int | None = None,
    output_format: str | None = None,
    recursive: bool = False,
    skip_existing: bool = False,
    tile_size: int | None = None,
    jpeg_quality: int | None = None,
    progress: ProgressReporter | None = None,
) -> BatchResult:
    """Process all images in a directory."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir) if output_dir else settings.output_path
    scale = scale or settings.default_scale
    output_format = output_format or settings.default_format
    progress = progress or ProgressReporter()

    images = find_images(input_dir, recursive=recursive)
    result = BatchResult(total=len(images))

    for i, img_path in enumerate(images):
        # Build output path preserving subdirectory structure
        rel = img_path.relative_to(input_dir)
        from upscaler.core.upscale_engine import _format_to_ext
        ext = _format_to_ext(output_format)
        model_name = model_id or "upscaled"
        out_name = f"{img_path.stem}_{scale}x_{model_name}{ext}"
        out_path = output_dir / rel.parent / out_name

        if skip_existing and out_path.exists():
            result.skipped += 1
            logger.info("Skipping (exists): %s", out_path)
            continue

        try:
            engine.upscale(
                input_path=img_path,
                output_path=out_path,
                model_id=model_id,
                scale=scale,
                output_format=output_format,
                tile_size=tile_size,
                jpeg_quality=jpeg_quality,
            )
            result.completed += 1
            result.outputs.append(str(out_path))
        except Exception as e:
            result.failed += 1
            result.errors.append(f"{img_path}: {e}")
            logger.error("Failed to process %s: %s", img_path, e)
            progress.emit(
                EventType.IMAGE_ERROR,
                path=str(img_path),
                error=str(e),
            )

        progress.emit(
            EventType.BATCH_PROGRESS,
            completed=result.completed + result.skipped + result.failed,
            total=result.total,
            current_file=img_path.name,
        )

    return result
