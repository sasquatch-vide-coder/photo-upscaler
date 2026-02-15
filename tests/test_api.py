"""Tests for FastAPI endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from upscaler.core.model_manager import ModelInfo


@pytest.fixture
def client():
    """Create a test client with mocked dependencies."""
    with patch('upscaler.api.dependencies.init_dependencies'):
        with patch('upscaler.api.dependencies.model_manager') as mock_mm:
            # Set up mock model manager
            mock_mm.list_models.return_value = [
                ModelInfo(
                    model_id="test_model",
                    filename="test_model.pth",
                    path="/fake/test_model.pth",
                    architecture="ESRGAN",
                    scale=4,
                    file_size_mb=64.0,
                ),
            ]
            mock_mm.is_loaded.return_value = False

            from upscaler.api.app import create_app
            app = create_app()
            yield TestClient(app)


class TestModelsEndpoint:
    def test_list_models(self, client):
        response = client.get("/api/models")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_available(self, client):
        response = client.get("/api/models/available")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0  # Should have registry entries


class TestSettingsEndpoint:
    def test_get_settings(self, client):
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert "tile_size" in data
        assert "fp16" in data

    def test_update_settings(self, client):
        response = client.put("/api/settings", json={
            "tile_size": 256,
            "tile_overlap": 32,
            "default_format": "png",
            "jpeg_quality": 90,
            "fp16": False,
            "default_scale": 2,
            "max_loaded_models": 2,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["tile_size"] == 256
        assert data["fp16"] is False
