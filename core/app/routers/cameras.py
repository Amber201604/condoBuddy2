"""CCTV Cameras router — passive streaming, NO AI detection."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import get_current_active_user, require_staff
from app.models import User
from app.models import Camera
from app.schemas import CameraCreate, CameraRead, CameraUpdate
from app.services.camera_service import get_stream_proxy

router = APIRouter(prefix="/cameras", tags=["CCTV"])


@router.get("/", response_model=List[CameraRead])
async def list_cameras(
    zone: str = None,
    camera_type: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = select(Camera)
    if zone:
        stmt = stmt.where(Camera.zone == zone)
    if camera_type:
        stmt = stmt.where(Camera.camera_type == camera_type)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=CameraRead, status_code=201)
async def create_camera(
    data: CameraCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    cam = Camera(
        name=data.name,
        location=data.location,
        rtsp_url=data.rtsp_url,
        camera_type=data.camera_type,
        zone=data.zone,
    )
    db.add(cam)
    await db.commit()
    await db.refresh(cam)
    return cam


@router.get("/{camera_id}", response_model=CameraRead)
async def get_camera(
    camera_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    cam = result.scalar_one_or_none()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cam


@router.patch("/{camera_id}", response_model=CameraRead)
async def update_camera(
    camera_id: UUID,
    data: CameraUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    cam = result.scalar_one_or_none()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cam, field, value)
    await db.commit()
    await db.refresh(cam)
    return cam


@router.delete("/{camera_id}")
async def delete_camera(
    camera_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    cam = result.scalar_one_or_none()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    await db.delete(cam)
    await db.commit()
    return {"message": "Camera deleted"}


@router.get("/{camera_id}/stream")
async def camera_stream(
    camera_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Proxy MJPEG stream from NVR connector. No AI processing."""
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    cam = result.scalar_one_or_none()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Return redirect to NVR connector stream URL or proxy it
    stream_url = cam.stream_url or f"http://nvr-connector:8001/stream/{camera_id}"
    return {"stream_url": stream_url, "camera_name": cam.name}


@router.post("/{camera_id}/heartbeat")
async def camera_heartbeat(
    camera_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Called by NVR connector or camera agent."""
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    cam = result.scalar_one_or_none()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    cam.status = "online"
    from app.models import utc_now
    cam.last_heartbeat = utc_now()
    await db.commit()
    return {"message": "Heartbeat received"}
