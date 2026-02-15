"""WebSocket endpoint for real-time progress broadcasting."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from upscaler.core.progress import ProgressEvent

logger = logging.getLogger(__name__)
router = APIRouter()

# Connected WebSocket clients
_clients: set[WebSocket] = set()
_event_queue: asyncio.Queue[dict] | None = None


def get_event_queue() -> asyncio.Queue[dict]:
    global _event_queue
    if _event_queue is None:
        _event_queue = asyncio.Queue()
    return _event_queue


def progress_to_ws_callback(event: ProgressEvent) -> None:
    """Callback that pushes progress events to the async queue for WebSocket broadcast."""
    queue = get_event_queue()
    data = {
        "type": event.event_type.value,
        **event.data,
    }
    try:
        queue.put_nowait(data)
    except asyncio.QueueFull:
        pass  # Drop if queue is full


async def broadcast_worker() -> None:
    """Background task that reads from queue and broadcasts to all WS clients."""
    queue = get_event_queue()
    while True:
        data = await queue.get()
        msg = json.dumps(data)
        dead: list[WebSocket] = []
        for ws in _clients:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _clients.discard(ws)


@router.websocket("/ws/progress")
async def ws_progress(websocket: WebSocket):
    """WebSocket endpoint for progress events."""
    await websocket.accept()
    _clients.add(websocket)
    try:
        while True:
            # Keep connection alive; client can send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(websocket)
