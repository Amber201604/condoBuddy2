"""Notifications router — push notifications, WebSocket events."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.core.security import get_current_user, get_current_active_user
from app.core.websocket import manager
from app.models import User
from app.schemas import PushTokenRegister

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """Real-time WebSocket connection for push notifications."""
    from jose import jwt, JWTError
    from app.config import get_settings

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008)
            return
    except JWTError:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user_id)
    await manager.join_room(user_id, "all")

    # Auto-join staff room for staff users
    # (simplified — in production, query user role from DB)

    try:
        while True:
            data = await websocket.receive_json()
            # Handle client messages: ping, join_room, etc.
            msg_type = data.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "join_room":
                await manager.join_room(user_id, data.get("room"))
            elif msg_type == "leave_room":
                await manager.leave_room(user_id, data.get("room"))
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


@router.post("/register-push-token")
async def register_push_token(
    data: PushTokenRegister,
    current_user: User = Depends(get_current_active_user),
):
    """Register FCM/APNs push token for mobile notifications."""
    # In production, store in Redis or DB
    return {
        "message": "Push token registered",
        "user_id": str(current_user.id),
        "platform": data.platform,
    }


@router.post("/send")
async def send_notification(
    title: str,
    body: str,
    user_id: UUID = None,
    room: str = None,
    data: dict = None,
    _: User = Depends(get_current_active_user),
):
    """Send a notification via WebSocket (and optionally push)."""
    payload = {
        "type": "notification",
        "data": {
            "title": title,
            "body": body,
            "extra": data or {},
        },
    }
    if user_id:
        await manager.send_to_user(str(user_id), payload)
    elif room:
        await manager.broadcast(payload, room=room)
    else:
        await manager.broadcast(payload)
    return {"message": "Notification sent"}
