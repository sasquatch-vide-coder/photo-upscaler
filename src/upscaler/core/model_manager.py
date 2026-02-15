"""Model scanning, loading via Spandrel, LRU caching, and metadata management."""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

import torch
import spandrel

from upscaler.core.config import settings
from upscaler.core.progress import EventType, ProgressReporter

logger = logging.getLogger(__name__)

MODEL_EXTENSIONS = {".pth", ".safetensors"}


@dataclass
class ModelInfo:
    """Metadata about a discovered model file."""
    model_id: str          # filename without extension
    filename: str          # full filename
    path: str              # absolute path
    architecture: str = "unknown"
    scale: int = 0
    input_channels: int = 3
    file_size_mb: float = 0.0


class ModelManager:
    """Scans for models, loads them via Spandrel with LRU caching."""

    def __init__(
        self,
        models_dir: Path | None = None,
        max_loaded: int | None = None,
        progress: ProgressReporter | None = None,
    ) -> None:
        self.models_dir = models_dir or settings.models_path
        self.max_loaded = max_loaded or settings.max_loaded_models
        self.progress = progress or ProgressReporter()

        self._registry: dict[str, ModelInfo] = {}       # model_id → info
        self._loaded: OrderedDict[str, Any] = OrderedDict()  # model_id → loaded model (LRU)
        self._fp16_incompatible: set[str] = set()  # models that don't support fp16
        self._cache_path = self.models_dir / ".model_cache.json"

    # --- Scanning ---

    def scan(self) -> list[ModelInfo]:
        """Scan models directory and populate registry with metadata."""
        self.models_dir.mkdir(parents=True, exist_ok=True)
        cached = self._load_metadata_cache()

        for file in sorted(self.models_dir.iterdir()):
            if file.suffix.lower() not in MODEL_EXTENSIONS:
                continue
            model_id = file.stem
            if model_id in cached:
                self._registry[model_id] = ModelInfo(**cached[model_id])
            else:
                info = ModelInfo(
                    model_id=model_id,
                    filename=file.name,
                    path=str(file),
                    file_size_mb=round(file.stat().st_size / (1024 * 1024), 1),
                )
                # Probe with Spandrel to get architecture/scale
                try:
                    self._probe_model(info, file)
                except Exception as e:
                    logger.warning("Failed to probe model %s: %s", model_id, e)

                self._registry[model_id] = info

        self._save_metadata_cache()
        return list(self._registry.values())

    def _probe_model(self, info: ModelInfo, path: Path) -> None:
        """Load model briefly to detect architecture and scale."""
        loader = spandrel.ModelLoader(device="cpu")
        model = loader.load_from_file(path)
        info.architecture = model.architecture.name
        info.scale = model.scale
        info.input_channels = model.input_channels
        del model
        torch.cuda.empty_cache()

    # --- Loading (LRU) ---

    def get_model(self, model_id: str) -> Any:
        """Get a loaded model, loading from disk if needed. Uses LRU eviction."""
        if model_id in self._loaded:
            self._loaded.move_to_end(model_id)
            return self._loaded[model_id]

        if model_id not in self._registry:
            raise KeyError(f"Unknown model: {model_id}. Run scan() first or check model files.")

        info = self._registry[model_id]
        self._evict_if_needed()

        self.progress.emit(EventType.MODEL_LOADING, model_id=model_id)
        logger.info("Loading model: %s", model_id)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        loader = spandrel.ModelLoader(device=device)
        model = loader.load_from_file(info.path)

        if settings.fp16 and device == "cuda" and model_id not in self._fp16_incompatible:
            model.model.half()

        model.model.eval()
        self._loaded[model_id] = model
        self.progress.emit(EventType.MODEL_LOADED, model_id=model_id)
        return model

    def reload_model_fp32(self, model_id: str) -> Any:
        """Reload a model in fp32 after fp16 failure. Marks it as fp16-incompatible."""
        logger.warning("Model %s is not compatible with fp16, reloading in fp32", model_id)
        self._fp16_incompatible.add(model_id)
        self.unload_model(model_id)
        return self.get_model(model_id)

    def unload_model(self, model_id: str) -> None:
        """Explicitly unload a model from GPU memory."""
        if model_id in self._loaded:
            del self._loaded[model_id]
            torch.cuda.empty_cache()
            logger.info("Unloaded model: %s", model_id)

    def unload_all(self) -> None:
        """Unload all models from GPU memory."""
        self._loaded.clear()
        torch.cuda.empty_cache()

    def _evict_if_needed(self) -> None:
        """Evict least-recently-used models if at capacity."""
        while len(self._loaded) >= self.max_loaded:
            evicted_id, _ = self._loaded.popitem(last=False)
            torch.cuda.empty_cache()
            logger.info("Evicted model from cache: %s", evicted_id)

    # --- Info ---

    def list_models(self) -> list[ModelInfo]:
        """Return all known models from the registry."""
        return list(self._registry.values())

    def get_model_info(self, model_id: str) -> ModelInfo | None:
        return self._registry.get(model_id)

    def is_loaded(self, model_id: str) -> bool:
        return model_id in self._loaded

    def loaded_model_ids(self) -> list[str]:
        return list(self._loaded.keys())

    # --- Metadata cache ---

    def _load_metadata_cache(self) -> dict[str, dict]:
        if self._cache_path.exists():
            try:
                with open(self._cache_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_metadata_cache(self) -> None:
        cache_data = {mid: asdict(info) for mid, info in self._registry.items()}
        try:
            with open(self._cache_path, "w") as f:
                json.dump(cache_data, f, indent=2)
        except OSError as e:
            logger.warning("Failed to save metadata cache: %s", e)
