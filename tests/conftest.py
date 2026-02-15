"""Shared fixtures for tests."""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch
from PIL import Image


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory."""
    return tmp_path


@pytest.fixture
def sample_image_path(tmp_path) -> Path:
    """Create a small test image and return its path."""
    img = Image.fromarray(
        np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8), "RGB"
    )
    path = tmp_path / "test_image.png"
    img.save(path)
    return path


@pytest.fixture
def sample_rgba_image_path(tmp_path) -> Path:
    """Create a test image with alpha channel."""
    img = Image.fromarray(
        np.random.randint(0, 255, (64, 64, 4), dtype=np.uint8), "RGBA"
    )
    path = tmp_path / "test_rgba.png"
    img.save(path)
    return path


@pytest.fixture
def sample_tensor() -> torch.Tensor:
    """Create a sample (1, 3, 64, 64) tensor in [0, 1]."""
    return torch.rand(1, 3, 64, 64)


@pytest.fixture
def models_dir(tmp_path) -> Path:
    """Create a temporary models directory."""
    d = tmp_path / "models"
    d.mkdir()
    return d
