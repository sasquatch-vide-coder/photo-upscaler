"""Tests for model manager: scanning, LRU cache, metadata."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from upscaler.core.model_manager import ModelManager, ModelInfo


class TestModelManagerScan:
    def test_scan_empty_dir(self, models_dir):
        manager = ModelManager(models_dir=models_dir, max_loaded=3)
        models = manager.scan()
        assert models == []

    def test_scan_finds_pth_files(self, models_dir):
        # Create fake model files
        (models_dir / "model_a.pth").write_bytes(b"fake")
        (models_dir / "model_b.safetensors").write_bytes(b"fake")
        (models_dir / "readme.txt").write_text("not a model")

        with patch.object(ModelManager, '_probe_model'):
            manager = ModelManager(models_dir=models_dir, max_loaded=3)
            models = manager.scan()

        ids = {m.model_id for m in models}
        assert "model_a" in ids
        assert "model_b" in ids
        assert len(models) == 2

    def test_metadata_cache_roundtrip(self, models_dir):
        (models_dir / "test.pth").write_bytes(b"fake")

        with patch.object(ModelManager, '_probe_model'):
            manager = ModelManager(models_dir=models_dir, max_loaded=3)
            manager.scan()

        # Verify cache file was written
        cache_path = models_dir / ".model_cache.json"
        assert cache_path.exists()

        data = json.loads(cache_path.read_text())
        assert "test" in data

    def test_list_models(self, models_dir):
        manager = ModelManager(models_dir=models_dir, max_loaded=3)
        manager._registry["test"] = ModelInfo(
            model_id="test",
            filename="test.pth",
            path=str(models_dir / "test.pth"),
            architecture="ESRGAN",
            scale=4,
        )
        models = manager.list_models()
        assert len(models) == 1
        assert models[0].model_id == "test"


class TestModelManagerLRU:
    def test_is_loaded(self, models_dir):
        manager = ModelManager(models_dir=models_dir, max_loaded=3)
        assert not manager.is_loaded("test")

    def test_loaded_model_ids(self, models_dir):
        manager = ModelManager(models_dir=models_dir, max_loaded=3)
        assert manager.loaded_model_ids() == []

    def test_eviction(self, models_dir):
        """With max_loaded=2, loading a 3rd model should evict the oldest."""
        manager = ModelManager(models_dir=models_dir, max_loaded=2)

        # Manually place items in the loaded cache
        manager._loaded["a"] = MagicMock()
        manager._loaded["b"] = MagicMock()

        # Evict check
        manager._evict_if_needed()
        assert "a" not in manager._loaded
        assert "b" in manager._loaded

    def test_unload_model(self, models_dir):
        manager = ModelManager(models_dir=models_dir, max_loaded=3)
        manager._loaded["test"] = MagicMock()
        assert manager.is_loaded("test")

        manager.unload_model("test")
        assert not manager.is_loaded("test")

    def test_unload_all(self, models_dir):
        manager = ModelManager(models_dir=models_dir, max_loaded=3)
        manager._loaded["a"] = MagicMock()
        manager._loaded["b"] = MagicMock()
        manager.unload_all()
        assert len(manager.loaded_model_ids()) == 0
