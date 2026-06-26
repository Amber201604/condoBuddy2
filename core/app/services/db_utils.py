"""Shared database utilities to reduce boilerplate across routers."""
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_or_404(
    db: AsyncSession,
    model,
    record_id: UUID,
    detail: str = "Record not found",
):
    """Fetch a record by primary key or raise 404."""
    result = await db.execute(select(model).where(model.id == record_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail=detail)
    return obj


def check_resident_access(current_user: User, owner_id: UUID):
    """Raise 403 if a resident tries to access another resident's resource."""
    if current_user.role == "resident" and owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
