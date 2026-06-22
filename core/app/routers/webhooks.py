"""Webhook router — receives events from Frappe frontend."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class FacilityBookingWebhook(BaseModel):
    booking_id: str
    facility: str
    resident: str
    unit: str
    booking_date: str
    start_time: str
    end_time: str
    status: str
    event: str  # created, cancelled, updated


class VisitorWebhook(BaseModel):
    visitor_id: str
    visitor_name: str
    visitor_phone: Optional[str] = None
    host_resident: str
    host_unit: Optional[str] = None
    visit_type: str
    expected_arrival: Optional[str] = None
    expected_departure: Optional[str] = None
    qr_code: Optional[str] = None
    status: str


class IoTAlertWebhook(BaseModel):
    device_id: str
    location: str
    timestamp: str
    event_type: str
    type: str  # iot, cctv
    message: Optional[str] = None


class AccessLogWebhook(BaseModel):
    timestamp: str
    event_type: str
    device_id: str
    location: Optional[str] = None
    resident: Optional[str] = None
    unit: Optional[str] = None
    visitor: Optional[str] = None
    access_granted: bool = True
    method: str = "Unknown"


@router.post("/facility-booking")
async def receive_facility_booking(payload: FacilityBookingWebhook):
    """Receive facility booking events from Frappe."""
    # TODO: Store in core database or sync with local state
    # For now, just acknowledge receipt
    return {
        "status": "received",
        "booking_id": payload.booking_id,
        "event": payload.event,
    }


@router.post("/visitor")
async def receive_visitor(payload: VisitorWebhook):
    """Receive visitor pre-registration events from Frappe."""
    return {
        "status": "received",
        "visitor_id": payload.visitor_id,
        "visitor_name": payload.visitor_name,
    }


@router.post("/iot-alert")
async def receive_iot_alert(payload: IoTAlertWebhook):
    """Receive IoT sensor alerts from Frappe or directly from sensors."""
    # TODO: Trigger notifications, log to database
    return {
        "status": "received",
        "device_id": payload.device_id,
        "event_type": payload.event_type,
    }


@router.post("/access-log")
async def receive_access_log(payload: AccessLogWebhook):
    """Receive access control events from Frappe or gate devices."""
    # TODO: Store access log in core database
    return {
        "status": "received",
        "device_id": payload.device_id,
        "event_type": payload.event_type,
        "access_granted": payload.access_granted,
    }


@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoint."""
    return {"status": "ok", "service": "webhooks"}
