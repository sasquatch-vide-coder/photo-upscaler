"""Tests for upscale engine: chaining logic, output dimensions."""

import pytest

from upscaler.core.upscale_engine import _compute_passes, _lanczos_resize, _format_to_ext
import torch


class TestComputePasses:
    def test_native_scale(self):
        assert _compute_passes(4, 4) == 1

    def test_target_less_than_native(self):
        assert _compute_passes(2, 4) == 1

    def test_8x_from_4x_model(self):
        # 4^2 = 16, need 2 passes
        assert _compute_passes(8, 4) == 2

    def test_8x_from_2x_model(self):
        # 2^3 = 8, need 3 passes
        assert _compute_passes(8, 2) == 3

    def test_large_target(self):
        # 4^3 = 64, 3 passes needed for 32x
        assert _compute_passes(32, 4) == 3


class TestLanczosResize:
    def test_downscale(self):
        tensor = torch.rand(1, 3, 200, 200)
        result = _lanczos_resize(tensor, 100, 100)
        assert result.shape == (1, 3, 100, 100)

    def test_values_in_range(self):
        tensor = torch.rand(1, 3, 100, 100)
        result = _lanczos_resize(tensor, 50, 50)
        assert result.min() >= 0.0
        assert result.max() <= 1.0


class TestFormatToExt:
    def test_common_formats(self):
        assert _format_to_ext("png") == ".png"
        assert _format_to_ext("jpg") == ".jpg"
        assert _format_to_ext("jpeg") == ".jpg"
        assert _format_to_ext("webp") == ".webp"

    def test_case_insensitive(self):
        assert _format_to_ext("PNG") == ".png"
        assert _format_to_ext("Jpg") == ".jpg"

    def test_unknown_defaults_to_png(self):
        assert _format_to_ext("bla") == ".png"
