"""WebSocket connection manager for real-time updates."""
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections by user and by room/topic."""

    def __init__(self):
        # user_id -> list of WebSocket connections
        self.user_connections: Dict[str, List[WebSocket]] = {}
        # room/topic -> set of user_ids
        self.rooms: Dict[str, set] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)
        logger.debug("WebSocket connected for user %s", user_id)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.user_connections:
            self.user_connections[user_id] = [
                ws for ws in self.user_connections[user_id] if ws != websocket
            ]
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        logger.debug("WebSocket disconnected for user %s", user_id)

    async def send_to_user(self, user_id: str, message: dict):
        if user_id not in self.user_connections:
            return
        dead = []
        for ws in self.user_connections[user_id]:
            try:
                await ws.send_json(message)
            except Exception as exc:
                logger.warning("Failed to send to user %s, removing dead connection: %s", user_id, exc)
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, user_id)

    async def broadcast(self, message: dict, room: str = None):
        """Broadcast to all or to a room."""
        targets: List[tuple] = []
        if room:
            for uid in self.rooms.get(room, set()):
                for ws in self.user_connections.get(uid, []):
                    targets.append((ws, uid))
        else:
            for uid, conns in self.user_connections.items():
                for ws in conns:
                    targets.append((ws, uid))

        dead = []
        for ws, uid in targets:
            try:
                await ws.send_json(message)
            except Exception as exc:
                logger.warning("Broadcast failed for user %s, removing dead connection: %s", uid, exc)
                dead.append((ws, uid))
        for ws, uid in dead:
            self.disconnect(ws, uid)

    async def join_room(self, user_id: str, room: str):
        if room not in self.rooms:
            self.rooms[room] = set()
        self.rooms[room].add(user_id)

    async def leave_room(self, user_id: str, room: str):
        if room in self.rooms:
            self.rooms[room].discard(user_id)


manager = ConnectionManager()
