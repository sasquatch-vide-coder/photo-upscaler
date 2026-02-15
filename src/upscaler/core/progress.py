"""Callback protocol for progress reporting across CLI and WebSocket."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Protocol


class EventType(str, Enum):
    MODEL_LOADING = "model_loading"
    MODEL_LOADED = "model_loaded"
    TILE_PROGRESS = "tile_progress"
    IMAGE_COMPLETE = "image_complete"
    IMAGE_ERROR = "image_error"
    BATCH_PROGRESS = "batch_progress"
    COMPARISON_MODEL_START = "comparison_model_start"
    COMPARISON_MODEL_DONE = "comparison_model_done"
    DOWNLOAD_PROGRESS = "download_progress"


@dataclass
class ProgressEvent:
    event_type: EventType
    data: dict[str, Any] = field(default_factory=dict)


class ProgressCallback(Protocol):
    def __call__(self, event: ProgressEvent) -> None: ...


class ProgressReporter:
    """Collects callbacks and dispatches progress events to all of them."""

    def __init__(self) -> None:
        self._callbacks: list[ProgressCallback] = []

    def add_callback(self, cb: ProgressCallback) -> None:
        self._callbacks.append(cb)

    def remove_callback(self, cb: ProgressCallback) -> None:
        self._callbacks.remove(cb)

    def emit(self, event_type: EventType, **data: Any) -> None:
        event = ProgressEvent(event_type=event_type, data=data)
        for cb in self._callbacks:
            cb(event)
