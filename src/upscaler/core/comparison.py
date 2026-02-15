"""Multi-model comparison runner — sequentially upscale with each model."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from upscaler.core.config import settings
from upscaler.core.image_io import load_image_as_tensor, save_tensor_as_image
from upscaler.core.model_manager import ModelManager
from upscaler.core.progress import EventType, ProgressReporter
from upscaler.core.tiling import process_tiles
from upscaler.core.upscale_engine import _compute_passes, _lanczos_resize, _format_to_ext

import torch

logger = logging.getLogger(__name__)


@dataclass
class ModelResult:
    model_id: str
    output_path: str
    duration_seconds: float
    success: bool = True
    error: str | None = None


@dataclass
class ComparisonResult:
    input_path: str
    scale: int
    results: list[ModelResult] = field(default_factory=list)


class ComparisonRunner:
    """Run an image through multiple models sequentially, managing VRAM."""

    def __init__(
        self,
        model_manager: ModelManager,
        progress: ProgressReporter | None = None,
    ) -> None:
        self.model_manager = model_manager
        self.progress = progress or ProgressReporter()

    def compare(
        self,
        input_path: str | Path,
        model_ids: list[str],
        scale: int | None = None,
        output_dir: str | Path | None = None,
        output_format: str | None = None,
        tile_size: int | None = None,
        tile_overlap: int | None = None,
        jpeg_quality: int | None = None,
    ) -> ComparisonResult:
        """Run comparison across all requested models."""
        input_path = Path(input_path)
        scale = scale or settings.default_scale
        output_format = output_format or settings.default_format
        tile_size = tile_size or settings.tile_size
        tile_overlap = tile_overlap or settings.tile_overlap
        jpeg_quality = jpeg_quality or settings.jpeg_quality
        output_dir = Path(output_dir) if output_dir else settings.output_path

        output_dir.mkdir(parents=True, exist_ok=True)

        result = ComparisonResult(input_path=str(input_path), scale=scale)

        for model_id in model_ids:
            self.progress.emit(EventType.COMPARISON_MODEL_START, model_id=model_id)
            start = time.perf_counter()

            try:
                output_path = self._upscale_single(
                    input_path, model_id, scale, output_dir,
                    output_format, tile_size, tile_overlap, jpeg_quality,
                )
                duration = time.perf_counter() - start
                result.results.append(ModelResult(
                    model_id=model_id,
                    output_path=str(output_path),
                    duration_seconds=round(duration, 2),
                ))
            except Exception as e:
                duration = time.perf_counter() - start
                logger.error("Model %s failed: %s", model_id, e)
                result.results.append(ModelResult(
                    model_id=model_id,
                    output_path="",
                    duration_seconds=round(duration, 2),
                    success=False,
                    error=str(e),
                ))

            self.progress.emit(
                EventType.COMPARISON_MODEL_DONE,
                model_id=model_id,
                success=result.results[-1].success,
            )

            # Unload model to free VRAM for next
            self.model_manager.unload_model(model_id)

        return result

    def _upscale_single(
        self,
        input_path: Path,
        model_id: str,
        scale: int,
        output_dir: Path,
        output_format: str,
        tile_size: int,
        tile_overlap: int,
        jpeg_quality: int,
        _fp32_retry: bool = False,
    ) -> Path:
        """Upscale a single image with one model."""
        model = self.model_manager.get_model(model_id)
        model_scale = model.scale
        device = next(model.model.parameters()).device
        use_fp16 = settings.fp16 and device.type == "cuda" and not _fp32_retry

        img_tensor = load_image_as_tensor(input_path, device=str(device))
        if use_fp16:
            img_tensor = img_tensor.half()

        passes_needed = _compute_passes(scale, model_scale)
        current = img_tensor

        try:
            for pass_idx in range(passes_needed):
                def process_fn(tile: torch.Tensor, _model=model) -> torch.Tensor:
                    return _model(tile)

                def tile_progress(done: int, total: int) -> None:
                    self.progress.emit(
                        EventType.TILE_PROGRESS,
                        model_id=model_id,
                        tiles_done=done,
                        tiles_total=total,
                    )

                current = process_tiles(
                    current, process_fn, model_scale, tile_size, tile_overlap, tile_progress,
                )
        except RuntimeError as e:
            err_msg = str(e).lower()
            is_dtype_error = "expected scalar type" in err_msg or "half" in err_msg or "float" in err_msg
            if is_dtype_error and not _fp32_retry:
                # fp16 incompatible — reload in fp32 and retry
                self.model_manager.reload_model_fp32(model_id)
                return self._upscale_single(
                    input_path, model_id, scale, output_dir,
                    output_format, tile_size, tile_overlap, jpeg_quality,
                    _fp32_retry=True,
                )
            raise

        achieved_scale = model_scale ** passes_needed
        if achieved_scale != scale:
            _, _, oh, ow = img_tensor.shape
            target_h, target_w = oh * scale, ow * scale
            current = _lanczos_resize(current, target_w, target_h)

        if current.dtype == torch.float16:
            current = current.float()

        ext = _format_to_ext(output_format)
        out_name = f"{input_path.stem}_{scale}x_{model_id}{ext}"
        out_path = output_dir / out_name

        save_tensor_as_image(current, out_path, format=output_format, jpeg_quality=jpeg_quality)
        return out_path
