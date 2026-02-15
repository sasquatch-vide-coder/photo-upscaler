"""Tests for tiling module: split, blend, reassembly."""

import torch
import pytest

from upscaler.core.tiling import compute_tiles, extract_tile, process_tiles


class TestComputeTiles:
    def test_single_tile_small_image(self):
        tiles = compute_tiles(64, 64, tile_size=512, overlap=32)
        assert len(tiles) == 1
        assert tiles[0].x == 0
        assert tiles[0].y == 0
        assert tiles[0].width == 64
        assert tiles[0].height == 64

    def test_multiple_tiles(self):
        tiles = compute_tiles(1024, 1024, tile_size=512, overlap=32)
        assert len(tiles) > 1

    def test_tiles_cover_image(self):
        w, h = 1000, 800
        tiles = compute_tiles(w, h, tile_size=256, overlap=32)

        # Every pixel should be covered by at least one tile
        covered = set()
        for tile in tiles:
            for y in range(tile.y, tile.y + tile.height):
                for x in range(tile.x, tile.x + tile.width):
                    covered.add((x, y))

        for y in range(h):
            for x in range(w):
                assert (x, y) in covered, f"Pixel ({x}, {y}) not covered"

    def test_tile_positions_within_bounds(self):
        w, h = 500, 300
        tiles = compute_tiles(w, h, tile_size=128, overlap=16)
        for tile in tiles:
            assert tile.x >= 0
            assert tile.y >= 0
            assert tile.x + tile.width <= w
            assert tile.y + tile.height <= h


class TestExtractTile:
    def test_extract_tile(self):
        image = torch.rand(1, 3, 100, 100)
        tiles = compute_tiles(100, 100, tile_size=50, overlap=10)
        for tile in tiles:
            extracted = extract_tile(image, tile)
            assert extracted.shape == (1, 3, tile.height, tile.width)


class TestProcessTiles:
    def test_identity_processing(self):
        """Process with identity function (scale=1) should return similar result."""
        image = torch.rand(1, 3, 128, 128)

        def identity(tile):
            return tile

        result = process_tiles(image, identity, scale=1, tile_size=64, overlap=16)
        assert result.shape == image.shape
        # Should be close to original (blending may introduce small differences)
        assert torch.allclose(result, image, atol=0.1)

    def test_upscale_processing(self):
        """Process with 2x upscale should double dimensions."""
        image = torch.rand(1, 3, 64, 64)

        def upscale_2x(tile):
            return torch.nn.functional.interpolate(tile, scale_factor=2, mode='bilinear', align_corners=False)

        result = process_tiles(image, upscale_2x, scale=2, tile_size=32, overlap=8)
        assert result.shape == (1, 3, 128, 128)

    def test_progress_callback(self):
        """Progress callback should be called for each tile."""
        image = torch.rand(1, 3, 128, 128)
        calls = []

        def identity(tile):
            return tile

        def progress(done, total):
            calls.append((done, total))

        process_tiles(image, identity, scale=1, tile_size=64, overlap=16, progress_fn=progress)
        assert len(calls) > 0
        # Last call should show all tiles done
        assert calls[-1][0] == calls[-1][1]
