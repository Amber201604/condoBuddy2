"""WebSocket connection manager for real-time updates."""
from typing import Dict, List
from fastapi import WebSocket


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

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.user_connections:
            self.user_connections[user_id] = [
                ws for ws in self.user_connections[user_id] if ws != websocket
            ]
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict):
        if user_id not in self.user_connections:
            return
        dead = []
        for ws in self.user_connections[user_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, user_id)

    async def broadcast(self, message: dict, room: str = None):
        """Broadcast to all or to a room."""
        targets = []
        if room:
            for uid in self.rooms.get(room, set()):
                targets.extend(self.user_connections.get(uid, []))
        else:
            for conns in self.user_connections.values():
                targets.extend(conns)

        dead = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append((ws, None))  # simplified

    async def join_room(self, user_id: str, room: str):
        if room not in self.rooms:
            self.rooms[room] = set()
        self.rooms[room].add(user_id)

    async def leave_room(self, user_id: str, room: str):
        if room in self.rooms:
            self.rooms[room].discard(user_id)


manager = ConnectionManager()
