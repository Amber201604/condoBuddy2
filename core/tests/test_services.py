"""Unit tests for services — notification_service, camera_service."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("MINIO_ENDPOINT", "")
os.environ.setdefault("MQTT_BROKER_HOST", "")

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.notification_service import send_push_notification, send_bulk_push
from app.services.camera_service import get_stream_proxy, fetch_snapshot


class TestNotificationService:
    @pytest.mark.asyncio
    async def test_send_push_notification(self):
        result = await send_push_notification("user-1", "Title", "Body")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_send_push_with_data(self):
        result = await send_push_notification(
            "user-1", "Title", "Body", data={"key": "val"}
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_send_bulk_push(self):
        result = await send_bulk_push(
            ["u1", "u2", "u3"], "Bulk Title", "Bulk Body"
        )
        assert result["success"] is True
        assert result["count"] == 3

    @pytest.mark.asyncio
    async def test_send_bulk_push_empty(self):
        result = await send_bulk_push([], "Title", "Body")
        assert result["count"] == 0


class TestCameraService:
    @pytest.mark.asyncio
    async def test_get_stream_proxy_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"stream_url": "http://proxy/stream/1"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.camera_service.httpx.AsyncClient", return_value=mock_client):
            url = await get_stream_proxy("cam-1")
            assert url == "http://proxy/stream/1"

    @pytest.mark.asyncio
    async def test_get_stream_proxy_not_found(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.camera_service.httpx.AsyncClient", return_value=mock_client):
            url = await get_stream_proxy("cam-missing")
            assert url is None

    @pytest.mark.asyncio
    async def test_get_stream_proxy_connection_error(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.camera_service.httpx.AsyncClient", return_value=mock_client):
            url = await get_stream_proxy("cam-1")
            assert url is None

    @pytest.mark.asyncio
    async def test_fetch_snapshot_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"\xff\xd8\xff\xe0"  # JPEG header bytes

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.camera_service.httpx.AsyncClient", return_value=mock_client):
            data = await fetch_snapshot("cam-1")
            assert data == b"\xff\xd8\xff\xe0"

    @pytest.mark.asyncio
    async def test_fetch_snapshot_failure(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.camera_service.httpx.AsyncClient", return_value=mock_client):
            data = await fetch_snapshot("cam-1")
            assert data is None
