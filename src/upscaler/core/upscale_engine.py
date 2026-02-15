"""Orchestrator: ties model loading, tiling, and image I/O together."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Optional

import torch
from PIL import Image

from upscaler.core.config import settings
from upscaler.core.image_io import load_image_as_tensor, save_tensor_as_image
from upscaler.core.model_manager import ModelManager
from upscaler.core.progress import EventType, ProgressReporter
from upscaler.core.tiling import process_tiles

logger = logging.getLogger(__name__)


class UpscaleEngine:
    """High-level upscaling engine supporting tiling, chaining, and progress."""

    def __init__(
        self,
        model_manager: ModelManager,
        progress: ProgressReporter | None = None,
    ) -> None:
        self.model_manager = model_manager
        self.progress = progress or ProgressReporter()

    def upscale(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        model_id: str | None = None,
        scale: int | None = None,
        output_format: str | None = None,
        tile_size: int | None = None,
        tile_overlap: int | None = None,
        jpeg_quality: int | None = None,
    ) -> Path:
        """Upscale a single image.

        Handles 8x by chaining passes (e.g., 4x model applied twice = 16x,
        then Lanczos downscale to exact 8x target).
        """
        input_path = Path(input_path)
        scale = scale or settings.default_scale
        output_format = output_format or settings.default_format
        tile_size = tile_size or settings.tile_size
        tile_overlap = tile_overlap or settings.tile_overlap
        jpeg_quality = jpeg_quality or settings.jpeg_quality

        # Determine output path
        if output_path is None:
            model_name = model_id or "upscaled"
            ext = _format_to_ext(output_format)
            out_name = f"{input_path.stem}_{scale}x_{model_name}{ext}"
            output_path = settings.output_path / out_name
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load model
        model = self.model_manager.get_model(model_id)
        model_scale = model.scale
        device = next(model.model.parameters()).device
        use_fp16 = settings.fp16 and device.type == "cuda"

        # Load image
        img_tensor = load_image_as_tensor(input_path, device=str(device))
        if use_fp16:
            img_tensor = img_tensor.half()

        # Determine how many passes needed
        passes_needed = _compute_passes(scale, model_scale)

        current = img_tensor
        try:
            for pass_idx in range(passes_needed):
                logger.info(
                    "Pass %d/%d (model scale=%dx)",
                    pass_idx + 1, passes_needed, model_scale,
                )

                def process_fn(tile: torch.Tensor, _model=model) -> torch.Tensor:
                    return _model(tile)

                def tile_progress(done: int, total: int, _pass=pass_idx) -> None:
                    self.progress.emit(
                        EventType.TILE_PROGRESS,
                        pass_num=_pass + 1,
                        total_passes=passes_needed,
                        tiles_done=done,
                        tiles_total=total,
                    )

                current = process_tiles(
                    current,
                    process_fn=process_fn,
                    scale=model_scale,
                    tile_size=tile_size,
                    overlap=tile_overlap,
                    progress_fn=tile_progress,
                )
        except RuntimeError as e:
            err_msg = str(e).lower()
            is_dtype_error = "expected scalar type" in err_msg or "half" in err_msg or "float" in err_msg
            if is_dtype_error and use_fp16:
                logger.warning("Model %s failed with fp16, retrying in fp32", model_id)
                self.model_manager.reload_model_fp32(model_id)
                return self.upscale(
                    input_path=input_path,
                    output_path=output_path,
                    model_id=model_id,
                    scale=scale,
                    output_format=output_format,
                    tile_size=tile_size,
                    tile_overlap=tile_overlap,
                    jpeg_quality=jpeg_quality,
                )
            raise

        # If total upscale overshot the target, downscale with Lanczos
        achieved_scale = model_scale ** passes_needed
        if achieved_scale != scale:
            _, _, oh, ow = img_tensor.shape
            target_h, target_w = oh * scale, ow * scale
            current = _lanczos_resize(current, target_w, target_h)

        # Convert back to float32 for saving
        if current.dtype == torch.float16:
            current = current.float()

        save_tensor_as_image(current, output_path, format=output_format, jpeg_quality=jpeg_quality)

        self.progress.emit(
            EventType.IMAGE_COMPLETE,
            input_path=str(input_path),
            output_path=str(output_path),
            scale=scale,
            model_id=model_id,
        )

        logger.info("Saved: %s", output_path)
        return output_path


def _compute_passes(target_scale: int, model_scale: int) -> int:
    """How many model passes to reach or exceed target scale."""
    if target_scale <= model_scale:
        return 1
    return math.ceil(math.log(target_scale) / math.log(model_scale))


def _lanczos_resize(tensor: torch.Tensor, width: int, height: int) -> torch.Tensor:
    """Downscale a (1, C, H, W) tensor to exact dimensions using Lanczos via PIL."""
    original_device = tensor.device
    if tensor.dtype == torch.float16:
        tensor = tensor.float()
    arr = tensor.squeeze(0).cpu().clamp(0, 1).permute(1, 2, 0).numpy()
    arr = (arr * 255).round().astype("uint8")
    img = Image.fromarray(arr, "RGB")
    img = img.resize((width, height), Image.Resampling.LANCZOS)

    import numpy as np
    arr = np.array(img).astype("float32") / 255.0
    result = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    return result.to(original_device)


def _format_to_ext(fmt: str) -> str:
    """Map format name to file extension."""
    mapping = {
        "png": ".png",
        "jpg": ".jpg",
        "jpeg": ".jpg",
        "webp": ".webp",
        "bmp": ".bmp",
        "tiff": ".tiff",
    }
    return mapping.get(fmt.lower(), ".png")
