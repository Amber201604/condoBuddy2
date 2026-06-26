"""Users router — admin & staff user management."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import get_current_user, require_staff, require_admin
from app.models import User
from app.schemas import UserRead, UserCreate
from app.services.db_utils import get_or_404
from app.services.user_service import create_user_in_db

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[UserRead])
async def list_users(
    role: str = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    return await get_or_404(db, User, user_id, "User not found")


@router.post("/", response_model=UserRead)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await create_user_in_db(db, user_data)


@router.patch("/{user_id}/activate")
async def activate_user(
    user_id: UUID,
    active: bool = True,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = await get_or_404(db, User, user_id, "User not found")
    user.is_active = active
    await db.commit()
    return {"message": f"User {'activated' if active else 'deactivated'}"}
