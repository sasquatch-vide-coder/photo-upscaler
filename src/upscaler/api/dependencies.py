"""Shared singletons for dependency injection across API routes."""

from __future__ import annotations

from upscaler.core.config import settings
from upscaler.core.model_manager import ModelManager
from upscaler.core.upscale_engine import UpscaleEngine
from upscaler.core.comparison import ComparisonRunner
from upscaler.core.progress import ProgressReporter

# Singletons initialized at app startup
progress_reporter: ProgressReporter | None = None
model_manager: ModelManager | None = None
upscale_engine: UpscaleEngine | None = None
comparison_runner: ComparisonRunner | None = None


def init_dependencies() -> None:
    """Initialize all shared singletons. Called during app lifespan startup."""
    global progress_reporter, model_manager, upscale_engine, comparison_runner

    progress_reporter = ProgressReporter()
    model_manager = ModelManager(progress=progress_reporter)
    model_manager.scan()
    upscale_engine = UpscaleEngine(model_manager=model_manager, progress=progress_reporter)
    comparison_runner = ComparisonRunner(model_manager=model_manager, progress=progress_reporter)


def cleanup_dependencies() -> None:
    """Cleanup on shutdown."""
    global model_manager
    if model_manager:
        model_manager.unload_all()


def get_model_manager() -> ModelManager:
    assert model_manager is not None, "Dependencies not initialized"
    return model_manager


def get_engine() -> UpscaleEngine:
    assert upscale_engine is not None, "Dependencies not initialized"
    return upscale_engine


def get_comparison_runner() -> ComparisonRunner:
    assert comparison_runner is not None, "Dependencies not initialized"
    return comparison_runner


def get_progress() -> ProgressReporter:
    assert progress_reporter is not None, "Dependencies not initialized"
    return progress_reporter
