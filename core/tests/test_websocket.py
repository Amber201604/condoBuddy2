"""Unit tests for core/websocket.py — ConnectionManager."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("MINIO_ENDPOINT", "")
os.environ.setdefault("MQTT_BROKER_HOST", "")

import asyncio
import pytest
from unittest.mock import AsyncMock

from app.core.websocket import ConnectionManager


def _make_ws():
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


def _run(coro):
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestConnectionManager:
    def test_connect_adds_user(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        _run(mgr.connect(ws, "u1"))
        assert "u1" in mgr.user_connections
        assert ws in mgr.user_connections["u1"]

    def test_disconnect_removes_websocket(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        _run(mgr.connect(ws, "u1"))
        mgr.disconnect(ws, "u1")
        assert "u1" not in mgr.user_connections

    def test_disconnect_keeps_other_connections(self):
        mgr = ConnectionManager()
        ws1 = _make_ws()
        ws2 = _make_ws()
        _run(mgr.connect(ws1, "u1"))
        _run(mgr.connect(ws2, "u1"))
        mgr.disconnect(ws1, "u1")
        assert ws2 in mgr.user_connections["u1"]
        assert ws1 not in mgr.user_connections["u1"]

    def test_disconnect_unknown_user(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        mgr.disconnect(ws, "unknown")  # should not raise

    def test_send_to_user(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        _run(mgr.connect(ws, "u1"))
        _run(mgr.send_to_user("u1", {"msg": "hello"}))
        ws.send_json.assert_awaited_once_with({"msg": "hello"})

    def test_send_to_user_no_connections(self):
        mgr = ConnectionManager()
        _run(mgr.send_to_user("nobody", {"msg": "hello"}))  # should not raise

    def test_send_to_user_removes_dead_connections(self):
        mgr = ConnectionManager()
        ws_good = _make_ws()
        ws_dead = _make_ws()
        ws_dead.send_json.side_effect = Exception("connection closed")
        _run(mgr.connect(ws_good, "u1"))
        _run(mgr.connect(ws_dead, "u1"))
        _run(mgr.send_to_user("u1", {"msg": "test"}))
        assert ws_dead not in mgr.user_connections["u1"]
        assert ws_good in mgr.user_connections["u1"]

    def test_broadcast_all(self):
        mgr = ConnectionManager()
        ws1 = _make_ws()
        ws2 = _make_ws()
        _run(mgr.connect(ws1, "u1"))
        _run(mgr.connect(ws2, "u2"))
        _run(mgr.broadcast({"type": "test"}))
        ws1.send_json.assert_awaited_once_with({"type": "test"})
        ws2.send_json.assert_awaited_once_with({"type": "test"})

    def test_broadcast_to_room(self):
        mgr = ConnectionManager()
        ws1 = _make_ws()
        ws2 = _make_ws()
        _run(mgr.connect(ws1, "u1"))
        _run(mgr.connect(ws2, "u2"))
        _run(mgr.join_room("u1", "staff"))
        _run(mgr.broadcast({"type": "alert"}, room="staff"))
        ws1.send_json.assert_awaited_once_with({"type": "alert"})
        ws2.send_json.assert_not_awaited()

    def test_join_and_leave_room(self):
        mgr = ConnectionManager()
        _run(mgr.join_room("u1", "room1"))
        assert "u1" in mgr.rooms["room1"]
        _run(mgr.leave_room("u1", "room1"))
        assert "u1" not in mgr.rooms["room1"]

    def test_leave_room_not_joined(self):
        mgr = ConnectionManager()
        _run(mgr.leave_room("u1", "nonexistent"))  # should not raise
