"""LPR (License Plate Recognition) Parking router."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.core.security import get_current_active_user, require_staff
from app.core.websocket import manager
from app.models import User, LPREvent
from app.schemas import LPREventCreate, LPREventRead
from app.services.db_utils import get_or_404

router = APIRouter(prefix="/lpr", tags=["LPR Parking"])


@router.get("/", response_model=List[LPREventRead])
async def list_lpr_events(
    direction: str = None,
    is_visitor: bool = None,
    plate_number: str = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    stmt = select(LPREvent).order_by(desc(LPREvent.timestamp)).limit(limit)
    if direction:
        stmt = stmt.where(LPREvent.direction == direction)
    if is_visitor is not None:
        stmt = stmt.where(LPREvent.is_visitor == is_visitor)
    if plate_number:
        stmt = stmt.where(LPREvent.plate_number.ilike(f"%{plate_number}%"))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=LPREventRead, status_code=201)
async def create_lpr_event(
    data: LPREventCreate,
    db: AsyncSession = Depends(get_db),
):
    """Called by LPR camera system when a plate is detected."""
    # Check if this is a known resident
    result = await db.execute(
        select(User).where(
            User.unit_number.isnot(None),
        )
    )
    # Simplified: in production, lookup plate-to-resident mapping
    is_visitor = True  # default

    event = LPREvent(
        plate_number=data.plate_number,
        direction=data.direction,
        confidence=data.confidence,
        parking_slot=data.parking_slot,
        is_visitor=is_visitor,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    # Broadcast to staff
    await manager.broadcast(
        {
            "type": "lpr_event",
            "data": {
                "plate_number": event.plate_number,
                "direction": event.direction,
                "is_visitor": event.is_visitor,
            },
        },
        room="staff",
    )
    return event


@router.get("/{event_id}", response_model=LPREventRead)
async def get_lpr_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    return await get_or_404(db, LPREvent, event_id, "LPR event not found")


@router.post("/{event_id}/mark-stolen")
async def mark_stolen(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    event = await get_or_404(db, LPREvent, event_id, "LPR event not found")
    event.is_stolen_alert = True
    await db.commit()

    await manager.broadcast(
        {
            "type": "stolen_vehicle_alert",
            "data": {
                "plate_number": event.plate_number,
                "direction": event.direction,
                "timestamp": event.timestamp.isoformat(),
            },
        },
        room="staff",
    )
    return {"message": "Marked as stolen vehicle alert"}
