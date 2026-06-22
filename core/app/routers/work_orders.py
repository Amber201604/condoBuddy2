"""Work Orders router."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.core.security import get_current_user, get_current_active_user, require_staff
from app.core.websocket import manager
from app.models import User
from app.models import WorkOrder
from app.schemas import WorkOrderCreate, WorkOrderRead, WorkOrderUpdate

router = APIRouter(prefix="/work-orders", tags=["Work Orders"])


@router.get("/", response_model=List[WorkOrderRead])
async def list_work_orders(
    status: str = None,
    priority: str = None,
    category: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = select(WorkOrder)
    if current_user.role == "resident":
        stmt = stmt.where(WorkOrder.resident_id == current_user.id)
    if status:
        stmt = stmt.where(WorkOrder.status == status)
    if priority:
        stmt = stmt.where(WorkOrder.priority == priority)
    if category:
        stmt = stmt.where(WorkOrder.category == category)
    stmt = stmt.order_by(desc(WorkOrder.created_at))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=WorkOrderRead, status_code=201)
async def create_work_order(
    data: WorkOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    wo = WorkOrder(
        resident_id=current_user.id,
        title=data.title,
        description=data.description,
        category=data.category,
        priority=data.priority,
        unit_number=data.unit_number or current_user.unit_number,
        images=data.images or [],
    )
    db.add(wo)
    await db.commit()
    await db.refresh(wo)

    # Notify staff via WebSocket
    await manager.broadcast(
        {"type": "new_work_order", "data": {"id": str(wo.id), "title": wo.title}},
        room="staff",
    )
    return wo


@router.get("/{wo_id}", response_model=WorkOrderRead)
async def get_work_order(
    wo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(WorkOrder).where(WorkOrder.id == wo_id))
    wo = result.scalar_one_or_none()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    if current_user.role == "resident" and wo.resident_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return wo


@router.patch("/{wo_id}", response_model=WorkOrderRead)
async def update_work_order(
    wo_id: UUID,
    data: WorkOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(WorkOrder).where(WorkOrder.id == wo_id))
    wo = result.scalar_one_or_none()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")

    # Residents can only update their own, staff can update any
    if current_user.role == "resident" and wo.resident_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(wo, field, value)

    await db.commit()
    await db.refresh(wo)

    await manager.send_to_user(
        str(wo.resident_id),
        {"type": "work_order_updated", "data": {"id": str(wo.id), "status": wo.status}},
    )
    return wo


@router.delete("/{wo_id}")
async def delete_work_order(
    wo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(WorkOrder).where(WorkOrder.id == wo_id))
    wo = result.scalar_one_or_none()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    if current_user.role == "resident" and wo.resident_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.delete(wo)
    await db.commit()
    return {"message": "Work order deleted"}
