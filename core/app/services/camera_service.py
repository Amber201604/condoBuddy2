"""Camera service — RTSP stream proxy helpers."""
import logging
from typing import Optional

import httpx
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


async def get_stream_proxy(camera_id: str) -> Optional[str]:
    """Get the proxied stream URL from NVR connector."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.nvr_base_url}/cameras/{camera_id}/stream")
            if resp.status_code == 200:
                return resp.json().get("stream_url")
            logger.warning(
                "NVR connector returned %d for camera %s stream",
                resp.status_code,
                camera_id,
            )
    except httpx.TimeoutException:
        logger.error("Timeout connecting to NVR connector for camera %s stream", camera_id)
    except httpx.ConnectError as exc:
        logger.error("Cannot reach NVR connector for camera %s: %s", camera_id, exc)
    except Exception as exc:
        logger.exception("Unexpected error fetching stream proxy for camera %s: %s", camera_id, exc)
    return None


async def fetch_snapshot(camera_id: str) -> Optional[bytes]:
    """Fetch a single JPEG snapshot from the NVR connector."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.nvr_base_url}/cameras/{camera_id}/snapshot")
            if resp.status_code == 200:
                return resp.content
            logger.warning(
                "NVR connector returned %d for camera %s snapshot",
                resp.status_code,
                camera_id,
            )
    except httpx.TimeoutException:
        logger.error("Timeout connecting to NVR connector for camera %s snapshot", camera_id)
    except httpx.ConnectError as exc:
        logger.error("Cannot reach NVR connector for camera %s: %s", camera_id, exc)
    except Exception as exc:
        logger.exception("Unexpected error fetching snapshot for camera %s: %s", camera_id, exc)
    return None
