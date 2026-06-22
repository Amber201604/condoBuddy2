"""Facility Booking router — proxies to Frappe for actual booking logic."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.config import get_settings
from app.core.security import get_current_active_user
from app.core.websocket import manager
from app.models import User
from app.models import FacilityBooking
from app.schemas import (
    FacilityBookingCreate, FacilityBookingRead, FacilityBookingUpdate
)

router = APIRouter(prefix="/facility-bookings", tags=["Facility Booking"])
settings = get_settings()


@router.get("/", response_model=List[FacilityBookingRead])
async def list_bookings(
    facility_type: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = select(FacilityBooking)
    if current_user.role == "resident":
        stmt = stmt.where(FacilityBooking.resident_id == current_user.id)
    if facility_type:
        stmt = stmt.where(FacilityBooking.facility_type == facility_type)
    if status:
        stmt = stmt.where(FacilityBooking.status == status)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=FacilityBookingRead, status_code=201)
async def create_booking(
    data: FacilityBookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a facility booking. Proxies to Frappe, caches locally."""
    # Check for conflicts
    conflict = await db.execute(
        select(FacilityBooking).where(
            and_(
                FacilityBooking.facility_name == data.facility_name,
                FacilityBooking.status.in_(["pending", "confirmed"]),
                FacilityBooking.start_time < data.end_time,
                FacilityBooking.end_time > data.start_time,
            )
        )
    )
    if conflict.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Time slot conflict")

    # In production, call Frappe API to create booking there
    # For now, create locally with a mock frappe_booking_id
    import uuid as uuid_mod
    booking = FacilityBooking(
        frappe_booking_id=f"CB-FRAPPE-{uuid_mod.uuid4().hex[:8].upper()}",
        facility_name=data.facility_name,
        facility_type=data.facility_type,
        resident_id=current_user.id,
        start_time=data.start_time,
        end_time=data.end_time,
        notes=data.notes,
        attendees_count=data.attendees_count,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    # TODO: Sync to Frappe via bridge
    # await sync_booking_to_frappe(booking)

    return booking


@router.get("/{booking_id}", response_model=FacilityBookingRead)
async def get_booking(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(FacilityBooking).where(FacilityBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if current_user.role == "resident" and booking.resident_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return booking


@router.patch("/{booking_id}", response_model=FacilityBookingRead)
async def update_booking(
    booking_id: UUID,
    data: FacilityBookingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(FacilityBooking).where(FacilityBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if current_user.role == "resident" and booking.resident_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(booking, field, value)

    await db.commit()
    await db.refresh(booking)

    # TODO: Sync update to Frappe
    return booking


@router.delete("/{booking_id}")
async def cancel_booking(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(FacilityBooking).where(FacilityBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if current_user.role == "resident" and booking.resident_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    booking.status = "cancelled"
    await db.commit()

    # TODO: Sync cancellation to Frappe
    return {"message": "Booking cancelled"}


@router.get("/facilities/available")
async def list_available_facilities(
    facility_type: str = None,
    start_time: str = None,
    end_time: str = None,
):
    """Return list of available facilities and their time slots."""
    # In production, query Frappe for facility availability
    # For now, return mock data
    facilities = [
        {"name": "Meeting Room A", "type": "meeting_room", "capacity": 10, "floor": "G"},
        {"name": "Meeting Room B", "type": "meeting_room", "capacity": 6, "floor": "G"},
        {"name": "Party Room", "type": "party_room", "capacity": 30, "floor": "2F"},
        {"name": "Gym", "type": "gym", "capacity": 20, "floor": "B1"},
        {"name": "Theatre", "type": "theatre", "capacity": 50, "floor": "3F"},
        {"name": "BBQ Area", "type": "bbq", "capacity": 15, "floor": "Rooftop"},
        {"name": "Study Room 1", "type": "study_room", "capacity": 4, "floor": "2F"},
        {"name": "Study Room 2", "type": "study_room", "capacity": 4, "floor": "2F"},
        {"name": "Game Room", "type": "game_room", "capacity": 8, "floor": "B1"},
    ]
    if facility_type:
        facilities = [f for f in facilities if f["type"] == facility_type]
    return {"facilities": facilities}
