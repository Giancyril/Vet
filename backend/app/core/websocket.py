"""
WebSocket Connection Manager & Telemetry Event Broadcaster.
Manages client connections per review/repository and broadcasts live agent progress.
"""
import asyncio
import json
from typing import Dict, List, Optional
from fastapi import WebSocket
from app.core.logging import logger


class ConnectionManager:
    def __init__(self):
        # Maps review_id -> list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Global channel for dashboard overview
        self.global_connections: List[WebSocket] = []

    async def connect_review(self, websocket: WebSocket, review_id: str):
        await websocket.accept()
        self.active_connections.setdefault(review_id, []).append(websocket)
        logger.info(f"[WS] Client connected to review stream: {review_id}")

    def disconnect_review(self, websocket: WebSocket, review_id: str):
        if review_id in self.active_connections:
            if websocket in self.active_connections[review_id]:
                self.active_connections[review_id].remove(websocket)
            if not self.active_connections[review_id]:
                del self.active_connections[review_id]
        logger.info(f"[WS] Client disconnected from review stream: {review_id}")

    async def connect_global(self, websocket: WebSocket):
        await websocket.accept()
        self.global_connections.append(websocket)
        logger.info("[WS] Client connected to global review feed")

    def disconnect_global(self, websocket: WebSocket):
        if websocket in self.global_connections:
            self.global_connections.remove(websocket)
        logger.info("[WS] Client disconnected from global review feed")

    async def broadcast_review_event(
        self,
        review_id: str,
        event_type: str,
        data: dict,
    ):
        """
        Broadcast a structured review progress event to all connected clients.
        event_type: "agent_started" | "secret_scanned" | "ast_analyzed" | "finding_discovered" | "health_calculated" | "review_finished"
        """
        payload = {
            "review_id": review_id,
            "event": event_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time(),
        }
        message_text = json.dumps(payload)

        # Send to review-specific listeners
        connections = self.active_connections.get(review_id, [])
        for conn in list(connections):
            try:
                await conn.send_text(message_text)
            except Exception as e:
                logger.warning(f"[WS] Failed to send message to client on {review_id}: {e}")
                self.disconnect_review(conn, review_id)

        # Send summary to global listeners
        for g_conn in list(self.global_connections):
            try:
                await g_conn.send_text(message_text)
            except Exception as e:
                logger.warning(f"[WS] Failed to send global broadcast: {e}")
                self.disconnect_global(g_conn)


ws_manager = ConnectionManager()
