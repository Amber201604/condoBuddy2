"""Packages router."""
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.core.security import get_current_active_user, require_staff
from app.core.websocket import manager
from app.models import User, Package, utc_now
from app.schemas import PackageCreate, PackageRead, PackagePickup
from app.services.db_utils import get_or_404, check_resident_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/packages", tags=["Packages"])


@router.get("/", response_model=List[PackageRead])
async def list_packages(
    status: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = select(Package)
    if current_user.role == "resident":
        stmt = stmt.where(Package.resident_id == current_user.id)
    if status:
        stmt = stmt.where(Package.status == status)
    stmt = stmt.order_by(desc(Package.created_at))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=PackageRead, status_code=201)
async def create_package(
    data: PackageCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    pkg = Package(
        resident_id=data.resident_id,
        tracking_number=data.tracking_number,
        carrier=data.carrier,
        description=data.description,
        locker_code=data.locker_code,
        locker_number=data.locker_number,
    )
    db.add(pkg)
    await db.commit()
    await db.refresh(pkg)

    try:
        await manager.send_to_user(
            str(pkg.resident_id),
            {
                "type": "package_arrived",
                "data": {
                    "id": str(pkg.id),
                    "description": pkg.description,
                    "locker_code": pkg.locker_code,
                },
            },
        )
    except Exception as exc:
        logger.error("Failed to notify resident %s of package arrival: %s", pkg.resident_id, exc)
    return pkg


@router.get("/{pkg_id}", response_model=PackageRead)
async def get_package(
    pkg_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    pkg = await get_or_404(db, Package, pkg_id, "Package not found")
    check_resident_access(current_user, pkg.resident_id)
    return pkg


@router.post("/{pkg_id}/pickup")
async def pickup_package(
    pkg_id: UUID,
    data: PackagePickup,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    pkg = await get_or_404(db, Package, pkg_id, "Package not found")
    check_resident_access(current_user, pkg.resident_id)

    if pkg.locker_code and pkg.locker_code != data.access_code:
        raise HTTPException(status_code=400, detail="Invalid access code")

    pkg.status = "picked_up"
    pkg.picked_up_at = utc_now()
    await db.commit()
    return {"message": "Package picked up successfully"}


@router.post("/{pkg_id}/notify")
async def notify_resident(
    pkg_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    pkg = await get_or_404(db, Package, pkg_id, "Package not found")

    pkg.status = "notified"
    pkg.notified_at = utc_now()
    await db.commit()

    try:
        await manager.send_to_user(
            str(pkg.resident_id),
            {
                "type": "package_notification",
                "data": {
                    "id": str(pkg.id),
                    "locker_code": pkg.locker_code,
                    "locker_number": pkg.locker_number,
                },
            },
        )
    except Exception as exc:
        logger.error("Failed to send package notification to resident %s: %s", pkg.resident_id, exc)
    return {"message": "Resident notified"}
