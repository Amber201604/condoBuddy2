"""Visitors router."""
from typing import List
from uuid import UUID
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.core.security import get_current_active_user
from app.core.websocket import manager
from app.models import User
from app.models import Visitor
from app.schemas import VisitorCreate, VisitorRead

router = APIRouter(prefix="/visitors", tags=["Visitors"])


def _gen_access_code() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


@router.get("/", response_model=List[VisitorRead])
async def list_visitors(
    status: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = select(Visitor)
    if current_user.role == "resident":
        stmt = stmt.where(Visitor.resident_id == current_user.id)
    if status:
        stmt = stmt.where(Visitor.status == status)
    stmt = stmt.order_by(desc(Visitor.visit_date))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=VisitorRead, status_code=201)
async def create_visitor(
    data: VisitorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    visitor = Visitor(
        resident_id=current_user.id,
        visitor_name=data.visitor_name,
        visitor_phone=data.visitor_phone,
        visit_purpose=data.visit_purpose,
        visit_date=data.visit_date,
        expected_duration_minutes=data.expected_duration_minutes,
        access_code=_gen_access_code(),
        notes=data.notes,
    )
    db.add(visitor)
    await db.commit()
    await db.refresh(visitor)
    return visitor


@router.get("/{visitor_id}", response_model=VisitorRead)
async def get_visitor(
    visitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Visitor).where(Visitor.id == visitor_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Visitor not found")
    if current_user.role == "resident" and v.resident_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return v


@router.post("/{visitor_id}/check-in")
async def visitor_check_in(
    visitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Visitor).where(Visitor.id == visitor_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Visitor not found")
    v.status = "checked_in"
    await db.commit()
    await manager.send_to_user(
        str(v.resident_id),
        {"type": "visitor_checked_in", "data": {"visitor_name": v.visitor_name}},
    )
    return {"message": "Visitor checked in"}


@router.post("/{visitor_id}/check-out")
async def visitor_check_out(
    visitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Visitor).where(Visitor.id == visitor_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Visitor not found")
    v.status = "checked_out"
    await db.commit()
    return {"message": "Visitor checked out"}


@router.delete("/{visitor_id}")
async def cancel_visitor(
    visitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Visitor).where(Visitor.id == visitor_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Visitor not found")
    if current_user.role == "resident" and v.resident_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    v.status = "cancelled"
    await db.commit()
    return {"message": "Visitor cancelled"}
