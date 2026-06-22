"""NVR Connector — RTSP stream proxy for CCTV cameras.

No AI detection. Just passes through MJPEG streams.
"""
import asyncio
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

CAMERA_REGISTRY = {}


def get_ffmpeg_cmd(rtsp_url: str, output_path: str) -> list:
    """Build ffmpeg command to convert RTSP to MJPEG stream."""
    return [
        "ffmpeg",
        "-i", rtsp_url,
        "-f", "mjpeg",
        "-q:v", "5",
        "-update", "1",
        output_path,
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Cleanup on shutdown


app = FastAPI(title="CondoBuddy2 NVR Connector", lifespan=lifespan)


@app.post("/cameras/{camera_id}/register")
async def register_camera(camera_id: str, rtsp_url: str):
    """Register a camera RTSP URL."""
    CAMERA_REGISTRY[camera_id] = {"rtsp_url": rtsp_url, "status": "registered"}
    return {"camera_id": camera_id, "status": "registered"}


@app.get("/cameras/{camera_id}/stream")
async def stream_camera(camera_id: str):
    """Return the proxied stream URL."""
    cam = CAMERA_REGISTRY.get(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not registered")
    # In production, this would return the actual proxy URL
    return {"camera_id": camera_id, "stream_url": f"/proxy/stream/{camera_id}.mjpeg"}


@app.get("/cameras/{camera_id}/snapshot")
async def camera_snapshot(camera_id: str):
    """Return a single JPEG snapshot."""
    cam = CAMERA_REGISTRY.get(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not registered")
    # Placeholder: in production, use ffmpeg to capture frame
    return {"camera_id": camera_id, "snapshot_url": f"/proxy/snapshot/{camera_id}.jpg"}


@app.get("/proxy/stream/{camera_id}.mjpeg")
async def proxy_mjpeg_stream(camera_id: str):
    """Proxy MJPEG stream using ffmpeg subprocess."""
    cam = CAMERA_REGISTRY.get(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not registered")

    rtsp_url = cam["rtsp_url"]

    async def generate():
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i", rtsp_url,
            "-f", "mjpeg",
            "-q:v", "5",
            "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            while True:
                chunk = await proc.stdout.read(4096)
                if not chunk:
                    break
                yield chunk
        finally:
            proc.terminate()
            await proc.wait()

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/health")
async def health():
    return {"status": "ok", "cameras_registered": len(CAMERA_REGISTRY)}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
