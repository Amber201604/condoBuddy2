"""Sensors router — IoT sensor alerts (smoke, motion, water leak, etc.)."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.core.security import get_current_active_user, require_staff
from app.core.websocket import manager
from app.models import User
from app.models import Sensor, SensorAlert
from app.schemas import SensorCreate, SensorRead, SensorAlertBase, SensorAlertRead, AlertAcknowledge

router = APIRouter(prefix="/sensors", tags=["Sensors"])


@router.get("/", response_model=List[SensorRead])
async def list_sensors(
    sensor_type: str = None,
    zone: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    stmt = select(Sensor)
    if sensor_type:
        stmt = stmt.where(Sensor.sensor_type == sensor_type)
    if zone:
        stmt = stmt.where(Sensor.zone == zone)
    if status:
        stmt = stmt.where(Sensor.status == status)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=SensorRead, status_code=201)
async def create_sensor(
    data: SensorCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    sensor = Sensor(
        name=data.name,
        sensor_type=data.sensor_type,
        location=data.location,
        zone=data.zone,
    )
    db.add(sensor)
    await db.commit()
    await db.refresh(sensor)
    return sensor


@router.get("/{sensor_id}", response_model=SensorRead)
async def get_sensor(
    sensor_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Sensor).where(Sensor.id == sensor_id))
    sensor = result.scalar_one_or_none()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor


@router.post("/{sensor_id}/reading")
async def sensor_reading(
    sensor_id: UUID,
    reading: dict,
    db: AsyncSession = Depends(get_db),
):
    """Receive sensor reading from IoT gateway."""
    result = await db.execute(select(Sensor).where(Sensor.id == sensor_id))
    sensor = result.scalar_one_or_none()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")

    sensor.last_reading = reading
    from app.models import utc_now
    sensor.last_heartbeat = utc_now()

    # Auto-detect alert conditions
    alert = None
    if sensor.sensor_type == "smoke" and reading.get("value", 0) > 50:
        sensor.status = "alert"
        alert = SensorAlert(
            sensor_id=sensor.id,
            alert_type="smoke_detected",
            severity="critical",
            message=f"Smoke detected at {sensor.location}",
            reading=reading,
        )
    elif sensor.sensor_type == "water_leak" and reading.get("leak", False):
        sensor.status = "alert"
        alert = SensorAlert(
            sensor_id=sensor.id,
            alert_type="water_leak",
            severity="critical",
            message=f"Water leak detected at {sensor.location}",
            reading=reading,
        )
    elif sensor.sensor_type == "temperature" and reading.get("value", 20) > 60:
        sensor.status = "alert"
        alert = SensorAlert(
            sensor_id=sensor.id,
            alert_type="high_temperature",
            severity="warning",
            message=f"High temperature at {sensor.location}: {reading.get('value')}°C",
            reading=reading,
        )
    else:
        sensor.status = "normal"

    if alert:
        db.add(alert)
        await manager.broadcast(
            {
                "type": "sensor_alert",
                "data": {
                    "sensor_id": str(sensor.id),
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "location": sensor.location,
                },
            },
            room="staff",
        )

    await db.commit()
    if alert:
        await db.refresh(alert)
        return {"status": "alert_triggered", "alert_id": str(alert.id)}
    return {"status": "normal"}


@router.get("/alerts", response_model=List[SensorAlertRead])
async def list_alerts(
    severity: str = None,
    acknowledged: bool = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    stmt = select(SensorAlert).order_by(desc(SensorAlert.created_at)).limit(limit)
    if severity:
        stmt = stmt.where(SensorAlert.severity == severity)
    if acknowledged is not None:
        if acknowledged:
            stmt = stmt.where(SensorAlert.acknowledged_at.isnot(None))
        else:
            stmt = stmt.where(SensorAlert.acknowledged_at.is_(None))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: UUID,
    data: AlertAcknowledge,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    result = await db.execute(select(SensorAlert).where(SensorAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if data.acknowledge:
        alert.acknowledged_by = current_user.id
        from app.models import utc_now
        alert.acknowledged_at = utc_now()
    await db.commit()
    return {"message": "Alert acknowledged"}
