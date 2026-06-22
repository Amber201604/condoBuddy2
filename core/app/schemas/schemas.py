"""CondoBuddy2 Core — Pydantic schemas."""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ─── User Schemas ───────────────────────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    unit_number: Optional[str] = None
    role: str = "resident"


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserRead(UserBase):
    id: UUID
    is_active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserRead] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


# ─── Facility Booking Schemas ───────────────────────────────────────────────

class FacilityBookingBase(BaseModel):
    facility_name: str
    facility_type: str
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None
    attendees_count: int = 1


class FacilityBookingCreate(FacilityBookingBase):
    pass


class FacilityBookingRead(FacilityBookingBase):
    id: UUID
    frappe_booking_id: Optional[str] = None
    resident_id: UUID
    status: str = "pending"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FacilityBookingUpdate(BaseModel):
    facility_name: Optional[str] = None
    facility_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    notes: Optional[str] = None
    attendees_count: Optional[int] = None
    status: Optional[str] = None


# ─── Work Order Schemas ─────────────────────────────────────────────────────

class WorkOrderBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: str
    priority: str = "medium"
    unit_number: Optional[str] = None
    images: Optional[List[str]] = None


class WorkOrderCreate(WorkOrderBase):
    pass


class WorkOrderRead(WorkOrderBase):
    id: UUID
    resident_id: UUID
    status: str = "open"
    assigned_to: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkOrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    unit_number: Optional[str] = None
    assigned_to: Optional[UUID] = None


# ─── Visitor Schemas ────────────────────────────────────────────────────────

class VisitorCreate(BaseModel):
    visitor_name: str
    visitor_phone: Optional[str] = None
    visit_purpose: Optional[str] = None
    visit_date: datetime
    expected_duration_minutes: int = 60
    notes: Optional[str] = None


class VisitorRead(BaseModel):
    id: UUID
    resident_id: UUID
    visitor_name: str
    visitor_phone: Optional[str] = None
    visit_purpose: Optional[str] = None
    visit_date: datetime
    expected_duration_minutes: int
    access_code: Optional[str] = None
    notes: Optional[str] = None
    status: str = "scheduled"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Package Schemas ────────────────────────────────────────────────────────

class PackageCreate(BaseModel):
    resident_id: UUID
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    description: Optional[str] = None
    locker_code: Optional[str] = None
    locker_number: Optional[str] = None


class PackageRead(BaseModel):
    id: UUID
    resident_id: UUID
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    description: Optional[str] = None
    locker_code: Optional[str] = None
    locker_number: Optional[str] = None
    status: str = "received"
    received_at: Optional[datetime] = None
    notified_at: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PackagePickup(BaseModel):
    access_code: Optional[str] = None


# ─── Access Log Schemas ─────────────────────────────────────────────────────

class AccessLogCreate(BaseModel):
    user_id: Optional[UUID] = None
    entry_point: str
    access_method: str
    direction: str = "entry"
    device_id: Optional[str] = None
    extra_data: Optional[dict] = None


class AccessLogRead(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    entry_point: str
    access_method: str
    direction: str
    device_id: Optional[str] = None
    success: bool
    extra_data: Optional[dict] = None
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


class AccessRequest(BaseModel):
    method: str  # nfc, qr_code, pin, visitor_qr
    payload: Optional[str] = None
    entry_point: str


# ─── Camera Schemas ─────────────────────────────────────────────────────────

class CameraCreate(BaseModel):
    name: str
    location: str
    rtsp_url: Optional[str] = None
    stream_url: Optional[str] = None
    camera_type: str = "fixed"
    zone: Optional[str] = None


class CameraRead(BaseModel):
    id: UUID
    name: str
    location: str
    rtsp_url: Optional[str] = None
    stream_url: Optional[str] = None
    camera_type: str
    zone: Optional[str] = None
    status: str = "offline"
    last_heartbeat: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    rtsp_url: Optional[str] = None
    stream_url: Optional[str] = None
    camera_type: Optional[str] = None
    zone: Optional[str] = None
    status: Optional[str] = None


# ─── Sensor Schemas ─────────────────────────────────────────────────────────

class SensorCreate(BaseModel):
    name: str
    sensor_type: str
    location: str
    zone: Optional[str] = None


class SensorRead(BaseModel):
    id: UUID
    name: str
    sensor_type: str
    location: str
    zone: Optional[str] = None
    status: str = "normal"
    last_reading: Optional[dict] = None
    last_heartbeat: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SensorAlertBase(BaseModel):
    alert_type: str
    severity: str = "warning"
    message: str
    reading: Optional[dict] = None


class SensorAlertRead(SensorAlertBase):
    id: UUID
    sensor_id: UUID
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertAcknowledge(BaseModel):
    acknowledge: bool = True


# ─── LPR Schemas ────────────────────────────────────────────────────────────

class LPREventCreate(BaseModel):
    plate_number: str
    direction: str
    confidence: float = 0.0
    parking_slot: Optional[str] = None


class LPREventRead(BaseModel):
    id: UUID
    plate_number: str
    direction: str
    confidence: float
    parking_slot: Optional[str] = None
    is_visitor: bool = True
    is_stolen_alert: bool = False
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Notification Schemas ───────────────────────────────────────────────────

class PushTokenRegister(BaseModel):
    token: str
    platform: str = "android"  # android, ios, web
