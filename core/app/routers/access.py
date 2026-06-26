"""Access Control router — NFC, QR, PIN entry logging."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.core.security import get_current_active_user, require_staff
from app.core.websocket import manager
from app.models import User
from app.models import AccessLog
from app.schemas import AccessLogCreate, AccessLogRead, AccessRequest

router = APIRouter(prefix="/access", tags=["Access Control"])


@router.get("/logs", response_model=List[AccessLogRead])
async def list_access_logs(
    entry_point: str = None,
    direction: str = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = select(AccessLog)
    if current_user.role == "resident":
        stmt = stmt.where(AccessLog.user_id == current_user.id)
    if entry_point:
        stmt = stmt.where(AccessLog.entry_point == entry_point)
    if direction:
        stmt = stmt.where(AccessLog.direction == direction)
    stmt = stmt.order_by(desc(AccessLog.timestamp)).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/log", response_model=AccessLogRead, status_code=201)
async def log_access(
    data: AccessLogCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    log = AccessLog(
        user_id=data.user_id,
        entry_point=data.entry_point,
        access_method=data.access_method,
        direction=data.direction,
        device_id=data.device_id,
        extra_data=data.extra_data or {},
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


@router.post("/grant")
async def grant_access(
    request: AccessRequest,
    db: AsyncSession = Depends(get_db),
):
    """Validate access request and log it. Called by access hardware or mobile app."""
    import logging
    _logger = logging.getLogger(__name__)

    user_id = None
    success = False

    # Simple validation logic — can be extended with actual NFC/QR validation
    if request.method == "nfc":
        # Lookup user by card ID (simplified)
        pass
    elif request.method == "qr_code":
        # Validate QR token
        pass
    elif request.method == "pin":
        # Validate PIN
        pass
    elif request.method == "visitor_qr":
        # Validate visitor access code
        from app.models import Visitor
        result = await db.execute(
            select(Visitor).where(
                Visitor.access_code == request.payload,
                Visitor.status == "scheduled",
            )
        )
        visitor = result.scalar_one_or_none()
        if visitor:
            success = True
            user_id = visitor.resident_id
            # Auto check-in
            visitor.status = "checked_in"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported access method: {request.method}")

    log = AccessLog(
        user_id=user_id,
        entry_point=request.entry_point,
        access_method=request.method,
        direction="entry",
        success=success,
        metadata={"payload": request.payload},
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    if success and user_id:
        try:
            await manager.send_to_user(
                str(user_id),
                {
                    "type": "access_granted",
                    "data": {"entry_point": request.entry_point},
                },
            )
        except Exception as exc:
            _logger.warning("Failed to notify user %s of access grant: %s", user_id, exc)

    return {"success": success, "log_id": str(log.id)}
