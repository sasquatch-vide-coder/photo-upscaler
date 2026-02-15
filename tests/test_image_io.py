"""Tests for image I/O module."""

import pytest
import torch
import numpy as np
from PIL import Image

from upscaler.core.image_io import (
    load_image_as_tensor,
    save_tensor_as_image,
    get_image_dimensions,
    SUPPORTED_EXTENSIONS,
)


class TestLoadImage:
    def test_load_rgb(self, sample_image_path):
        tensor = load_image_as_tensor(sample_image_path)
        assert tensor.shape == (1, 3, 64, 64)
        assert tensor.dtype == torch.float32
        assert tensor.min() >= 0.0
        assert tensor.max() <= 1.0

    def test_load_rgba_strips_alpha(self, sample_rgba_image_path):
        tensor = load_image_as_tensor(sample_rgba_image_path)
        assert tensor.shape[1] == 3  # Alpha stripped

    def test_load_unsupported_format(self, tmp_path):
        bad_file = tmp_path / "test.xyz"
        bad_file.write_text("not an image")
        with pytest.raises(ValueError, match="Unsupported"):
            load_image_as_tensor(bad_file)


class TestSaveImage:
    def test_save_png(self, tmp_path, sample_tensor):
        out = tmp_path / "out.png"
        save_tensor_as_image(sample_tensor, out, format="png")
        assert out.exists()
        img = Image.open(out)
        assert img.size == (64, 64)

    def test_save_jpg(self, tmp_path, sample_tensor):
        out = tmp_path / "out.jpg"
        save_tensor_as_image(sample_tensor, out, format="jpg", jpeg_quality=85)
        assert out.exists()

    def test_save_webp(self, tmp_path, sample_tensor):
        out = tmp_path / "out.webp"
        save_tensor_as_image(sample_tensor, out, format="webp")
        assert out.exists()

    def test_save_creates_dirs(self, tmp_path, sample_tensor):
        out = tmp_path / "a" / "b" / "out.png"
        save_tensor_as_image(sample_tensor, out)
        assert out.exists()

    def test_roundtrip(self, tmp_path, sample_image_path):
        tensor = load_image_as_tensor(sample_image_path)
        out = tmp_path / "roundtrip.png"
        save_tensor_as_image(tensor, out)
        tensor2 = load_image_as_tensor(out)
        assert torch.allclose(tensor, tensor2, atol=1 / 255 + 0.01)


class TestGetDimensions:
    def test_get_dimensions(self, sample_image_path):
        w, h = get_image_dimensions(sample_image_path)
        assert w == 64
        assert h == 64
