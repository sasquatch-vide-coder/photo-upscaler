"""Tile splitting, overlap blending, and reassembly for large images."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Callable

import torch

logger = logging.getLogger(__name__)


@dataclass
class TilePosition:
    """Coordinates for a tile within the source image."""
    x: int
    y: int
    width: int
    height: int
    row: int
    col: int


def compute_tiles(
    img_width: int,
    img_height: int,
    tile_size: int = 512,
    overlap: int = 32,
) -> list[TilePosition]:
    """Compute tile positions to cover the image with overlap."""
    tiles = []
    step = tile_size - overlap

    rows = max(1, math.ceil((img_height - overlap) / step))
    cols = max(1, math.ceil((img_width - overlap) / step))

    for row in range(rows):
        for col in range(cols):
            x = min(col * step, max(0, img_width - tile_size))
            y = min(row * step, max(0, img_height - tile_size))
            w = min(tile_size, img_width - x)
            h = min(tile_size, img_height - y)
            tiles.append(TilePosition(x=x, y=y, width=w, height=h, row=row, col=col))

    return tiles


def extract_tile(image: torch.Tensor, tile: TilePosition) -> torch.Tensor:
    """Extract a tile from a (1, C, H, W) tensor."""
    return image[:, :, tile.y:tile.y + tile.height, tile.x:tile.x + tile.width]


def _build_blend_mask(h: int, w: int, overlap: int, scale: int, device: torch.device) -> torch.Tensor:
    """Build a linear gradient blend mask for tile overlap regions."""
    scaled_overlap = overlap * scale
    mask = torch.ones(1, 1, h, w, device=device)

    if scaled_overlap > 0:
        # Top edge fade
        if h > scaled_overlap:
            ramp = torch.linspace(0, 1, scaled_overlap, device=device)
            mask[:, :, :scaled_overlap, :] *= ramp.view(1, 1, -1, 1)
        # Left edge fade
        if w > scaled_overlap:
            ramp = torch.linspace(0, 1, scaled_overlap, device=device)
            mask[:, :, :, :scaled_overlap] *= ramp.view(1, 1, 1, -1)
        # Bottom edge fade
        if h > scaled_overlap:
            ramp = torch.linspace(1, 0, scaled_overlap, device=device)
            mask[:, :, -scaled_overlap:, :] *= ramp.view(1, 1, -1, 1)
        # Right edge fade
        if w > scaled_overlap:
            ramp = torch.linspace(1, 0, scaled_overlap, device=device)
            mask[:, :, :, -scaled_overlap:] *= ramp.view(1, 1, 1, -1)

    return mask


def process_tiles(
    image: torch.Tensor,
    process_fn: Callable[[torch.Tensor], torch.Tensor],
    scale: int,
    tile_size: int = 512,
    overlap: int = 32,
    progress_fn: Callable[[int, int], None] | None = None,
) -> torch.Tensor:
    """Split image into tiles, process each, blend and reassemble.

    Includes OOM recovery: on CUDA OOM, halve tile size and retry.
    """
    _, c, h, w = image.shape
    current_tile_size = tile_size

    while True:
        try:
            return _process_tiles_inner(
                image, process_fn, scale, current_tile_size, overlap, progress_fn
            )
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            new_size = max(64, current_tile_size // 2)
            if new_size == current_tile_size:
                raise
            logger.warning(
                "CUDA OOM with tile_size=%d, retrying with tile_size=%d",
                current_tile_size, new_size,
            )
            current_tile_size = new_size


def _process_tiles_inner(
    image: torch.Tensor,
    process_fn: Callable[[torch.Tensor], torch.Tensor],
    scale: int,
    tile_size: int,
    overlap: int,
    progress_fn: Callable[[int, int], None] | None,
) -> torch.Tensor:
    """Inner tile processing loop."""
    _, c, h, w = image.shape
    out_h, out_w = h * scale, w * scale

    tiles = compute_tiles(w, h, tile_size, overlap)
    total_tiles = len(tiles)

    # Accumulation buffers
    output = torch.zeros(1, c, out_h, out_w, device=image.device)
    weight = torch.zeros(1, 1, out_h, out_w, device=image.device)

    for i, tile in enumerate(tiles):
        tile_input = extract_tile(image, tile)
        with torch.no_grad():
            tile_output = process_fn(tile_input)

        _, _, th, tw = tile_output.shape
        ox, oy = tile.x * scale, tile.y * scale

        # Build blend mask
        is_edge_top = tile.row == 0
        is_edge_left = tile.col == 0
        mask = _build_blend_mask(th, tw, overlap, scale, tile_output.device)

        # Don't fade edges that are at the image boundary
        scaled_overlap = overlap * scale
        if is_edge_top and scaled_overlap > 0 and th > scaled_overlap:
            mask[:, :, :scaled_overlap, :] = 1.0
        if is_edge_left and scaled_overlap > 0 and tw > scaled_overlap:
            mask[:, :, :, :scaled_overlap] = 1.0

        # Check if this tile is at the bottom/right edge of the image
        tiles_list = compute_tiles(image.shape[3], image.shape[2], tile_size, overlap)
        max_row = max(t.row for t in tiles_list)
        max_col = max(t.col for t in tiles_list)
        if tile.row == max_row and scaled_overlap > 0 and th > scaled_overlap:
            mask[:, :, -scaled_overlap:, :] = 1.0
        if tile.col == max_col and scaled_overlap > 0 and tw > scaled_overlap:
            mask[:, :, :, -scaled_overlap:] = 1.0

        output[:, :, oy:oy + th, ox:ox + tw] += tile_output * mask
        weight[:, :, oy:oy + th, ox:ox + tw] += mask

        if progress_fn:
            progress_fn(i + 1, total_tiles)

    # Normalize by weight to complete the blend
    weight = weight.clamp(min=1e-8)
    output /= weight

    return output
