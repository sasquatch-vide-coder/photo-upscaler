"""Known model download URLs and first-run download helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import httpx

from upscaler.core.config import settings
from upscaler.core.progress import EventType, ProgressReporter

logger = logging.getLogger(__name__)


@dataclass
class RegistryEntry:
    key: str
    name: str
    url: str
    filename: str
    architecture: str
    scale: int


KNOWN_MODELS: list[RegistryEntry] = [
    RegistryEntry(
        key="RealESRGAN_x4plus",
        name="Real-ESRGAN x4+",
        url="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        filename="RealESRGAN_x4plus.pth",
        architecture="Real-ESRGAN",
        scale=4,
    ),
    RegistryEntry(
        key="RealESRGAN_x2plus",
        name="Real-ESRGAN x2+",
        url="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
        filename="RealESRGAN_x2plus.pth",
        architecture="Real-ESRGAN",
        scale=2,
    ),
    RegistryEntry(
        key="RealESRGAN_x4plus_anime_6B",
        name="Real-ESRGAN x4+ Anime 6B",
        url="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
        filename="RealESRGAN_x4plus_anime_6B.pth",
        architecture="Real-ESRGAN",
        scale=4,
    ),
    RegistryEntry(
        key="4xNomos8kDAT",
        name="4x Nomos8k DAT",
        url="https://github.com/Phhofm/models/releases/download/4xNomos8kDAT/4xNomos8kDAT.pth",
        filename="4xNomos8kDAT.pth",
        architecture="DAT",
        scale=4,
    ),
]


def list_available() -> list[RegistryEntry]:
    """Return all known downloadable models."""
    return list(KNOWN_MODELS)


def list_not_downloaded(models_dir: Path | None = None) -> list[RegistryEntry]:
    """Return registry entries for models not yet present on disk."""
    models_dir = models_dir or settings.models_path
    existing = {f.name for f in models_dir.iterdir()} if models_dir.exists() else set()
    return [m for m in KNOWN_MODELS if m.filename not in existing]


def get_entry(key: str) -> RegistryEntry | None:
    """Look up a registry entry by key."""
    for entry in KNOWN_MODELS:
        if entry.key == key:
            return entry
    return None


def download_model(
    key: str,
    models_dir: Path | None = None,
    progress: ProgressReporter | None = None,
) -> Path:
    """Download a model by registry key. Returns the local file path."""
    entry = get_entry(key)
    if entry is None:
        raise KeyError(f"Unknown model key: {key}. Use list_available() to see options.")

    models_dir = models_dir or settings.models_path
    models_dir.mkdir(parents=True, exist_ok=True)
    dest = models_dir / entry.filename

    if dest.exists():
        logger.info("Model already exists: %s", dest)
        return dest

    logger.info("Downloading %s from %s", entry.name, entry.url)

    with httpx.stream("GET", entry.url, follow_redirects=True, timeout=300) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress.emit(
                        EventType.DOWNLOAD_PROGRESS,
                        model_key=key,
                        downloaded=downloaded,
                        total=total,
                    )

    logger.info("Downloaded: %s (%.1f MB)", dest, dest.stat().st_size / (1024 * 1024))
    return dest


def is_models_dir_empty(models_dir: Path | None = None) -> bool:
    """Check if models directory has no model files."""
    models_dir = models_dir or settings.models_path
    if not models_dir.exists():
        return True
    return not any(
        f.suffix.lower() in {".pth", ".safetensors"}
        for f in models_dir.iterdir()
    )
