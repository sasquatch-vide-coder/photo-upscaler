"""Image loading, saving, and tensor conversion utilities."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import torch
from PIL import Image

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}


def load_image_as_tensor(path: str | Path, device: str = "cpu") -> torch.Tensor:
    """Load an image file and return a float32 tensor of shape (1, C, H, W) in [0, 1].

    RGBA images are converted to RGB with a warning. Unsupported formats raise ValueError.
    """
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported image format: {path.suffix}")

    img = Image.open(path)

    if img.mode == "RGBA":
        logger.warning("Image has alpha channel — stripping alpha: %s", path.name)
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    arr = np.array(img).astype(np.float32) / 255.0  # (H, W, 3)
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)  # (1, 3, H, W)
    return tensor.to(device)


def save_tensor_as_image(
    tensor: torch.Tensor,
    path: str | Path,
    format: str = "png",
    jpeg_quality: int = 95,
) -> Path:
    """Save a (1, C, H, W) or (C, H, W) float tensor in [0, 1] to an image file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if tensor.dim() == 4:
        tensor = tensor.squeeze(0)

    arr = tensor.detach().cpu().clamp(0, 1).permute(1, 2, 0).numpy()
    arr = (arr * 255.0).round().astype(np.uint8)
    img = Image.fromarray(arr, "RGB")

    save_kwargs: dict = {}
    if format.lower() in ("jpg", "jpeg"):
        format = "JPEG"
        save_kwargs["quality"] = jpeg_quality
    elif format.lower() == "webp":
        format = "WebP"
        save_kwargs["quality"] = jpeg_quality
    elif format.lower() == "png":
        format = "PNG"

    img.save(path, format=format, **save_kwargs)
    return path


def generate_thumbnail(
    path: str | Path, max_size: int = 256
) -> Image.Image:
    """Generate a thumbnail for preview purposes."""
    img = Image.open(path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return img


def get_image_dimensions(path: str | Path) -> tuple[int, int]:
    """Return (width, height) of an image without fully loading it."""
    with Image.open(path) as img:
        return img.size
