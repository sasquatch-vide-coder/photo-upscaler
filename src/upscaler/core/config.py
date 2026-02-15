"""Application configuration with YAML loading and environment variable support."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


def _find_project_root() -> Path:
    """Walk up from CWD looking for pyproject.toml, fall back to CWD."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return current


PROJECT_ROOT = _find_project_root()


def _load_yaml_config() -> dict:
    """Load config.yaml with fallback to config.default.yaml."""
    user_config = PROJECT_ROOT / "config.yaml"
    default_config = PROJECT_ROOT / "config.default.yaml"

    config_path = user_config if user_config.exists() else default_config
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


class Settings(BaseSettings):
    """Application settings loaded from YAML, env vars (UPSCALER_ prefix), and defaults."""

    model_config = {"env_prefix": "UPSCALER_"}

    # Paths
    models_dir: str = "models"
    output_dir: str = "output"
    temp_dir: str = "temp"

    # Upscaling
    default_scale: int = 4
    default_format: str = "png"
    jpeg_quality: int = 95

    # Tiling
    tile_size: int = 512
    tile_overlap: int = 32

    # Performance
    fp16: bool = True
    max_loaded_models: int = 3

    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    open_browser: bool = True

    # Temp cleanup
    temp_max_age_minutes: int = 60

    def resolve_path(self, path_str: str) -> Path:
        """Resolve a path relative to project root if not absolute."""
        p = Path(path_str)
        if p.is_absolute():
            return p
        return PROJECT_ROOT / p

    @property
    def models_path(self) -> Path:
        return self.resolve_path(self.models_dir)

    @property
    def output_path(self) -> Path:
        return self.resolve_path(self.output_dir)

    @property
    def temp_path(self) -> Path:
        return self.resolve_path(self.temp_dir)


def load_settings() -> Settings:
    """Load settings from YAML file, with env var overrides."""
    yaml_data = _load_yaml_config()
    return Settings(**yaml_data)


# Global singleton — import this elsewhere
settings = load_settings()
