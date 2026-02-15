"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelInfoSchema(BaseModel):
    model_id: str
    filename: str
    architecture: str = "unknown"
    scale: int = 0
    file_size_mb: float = 0.0
    is_loaded: bool = False


class RegistryModelSchema(BaseModel):
    key: str
    name: str
    architecture: str
    scale: int
    is_downloaded: bool = False


class DownloadRequest(BaseModel):
    model_key: str


class UpscaleRequest(BaseModel):
    model_id: str
    scale: int = 4
    output_format: str = "png"
    tile_size: int | None = None
    jpeg_quality: int | None = None


class CompareRequest(BaseModel):
    model_ids: list[str]
    scale: int = 4
    output_format: str = "png"
    tile_size: int | None = None
    jpeg_quality: int | None = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: float = 0.0
    results: list[dict] | None = None
    error: str | None = None


class ComparisonResultSchema(BaseModel):
    model_id: str
    image_id: str
    duration_seconds: float
    success: bool = True
    error: str | None = None


class ComparisonResponse(BaseModel):
    comparison_id: str
    input_image_id: str
    scale: int
    results: list[ComparisonResultSchema] = []


class SettingsSchema(BaseModel):
    tile_size: int = 512
    tile_overlap: int = 32
    default_format: str = "png"
    jpeg_quality: int = 95
    fp16: bool = True
    default_scale: int = 4
    max_loaded_models: int = 3
