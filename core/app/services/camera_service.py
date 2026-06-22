"""Camera service — RTSP stream proxy helpers."""
import asyncio
from typing import Optional

import httpx
from app.config import get_settings

settings = get_settings()


async def get_stream_proxy(camera_id: str) -> Optional[str]:
    """Get the proxied stream URL from NVR connector."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.nvr_base_url}/cameras/{camera_id}/stream")
            if resp.status_code == 200:
                return resp.json().get("stream_url")
    except Exception:
        pass
    return None


async def fetch_snapshot(camera_id: str) -> Optional[bytes]:
    """Fetch a single JPEG snapshot from the NVR connector."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.nvr_base_url}/cameras/{camera_id}/snapshot")
            if resp.status_code == 200:
                return resp.content
    except Exception:
        pass
    return None
