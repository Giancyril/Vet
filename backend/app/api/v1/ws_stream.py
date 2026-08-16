"""
WebSocket endpoint for real-time review stream telemetry.
Clients connect to /api/v1/ws/reviews/{review_id} to receive live events.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket import ws_manager
from app.core.logging import logger

router = APIRouter()


@router.websocket("/ws/reviews/{review_id}")
async def review_stream(websocket: WebSocket, review_id: str):
    """Real-time WebSocket stream for a specific review run."""
    await ws_manager.connect_review(websocket, review_id)
    try:
        while True:
            # Keep connection alive - actual data is pushed server-side
            data = await websocket.receive_text()
            # Echo heartbeats back for keep-alive ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect_review(websocket, review_id)
        logger.info(f"[WS] Review stream disconnected: {review_id}")


@router.websocket("/ws/feed")
async def global_review_feed(websocket: WebSocket):
    """Global dashboard feed broadcasting all active review events."""
    await ws_manager.connect_global(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect_global(websocket)
        logger.info("[WS] Global feed disconnected")
