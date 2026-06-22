"""CondoBuddy2 Core — SQLAlchemy models."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, JSON, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    unit_number = Column(String(50), nullable=True)
    role = Column(String(20), default="resident")  # resident, staff, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class FacilityBooking(Base):
    __tablename__ = "facility_bookings"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    frappe_booking_id = Column(String(100), nullable=True, index=True)
    facility_name = Column(String(255), nullable=False)
    facility_type = Column(String(50), nullable=False)
    resident_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text, nullable=True)
    attendees_count = Column(Integer, default=1)
    status = Column(String(20), default="pending")  # pending, confirmed, cancelled, completed
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    resident_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)  # maintenance, cleaning, security, etc.
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    status = Column(String(20), default="open")  # open, in_progress, resolved, closed
    unit_number = Column(String(50), nullable=True)
    images = Column(JSON, default=list)
    assigned_to = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    resident_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    visitor_name = Column(String(255), nullable=False)
    visitor_phone = Column(String(50), nullable=True)
    visit_purpose = Column(String(255), nullable=True)
    visit_date = Column(DateTime(timezone=True), nullable=False)
    expected_duration_minutes = Column(Integer, default=60)
    access_code = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(20), default="scheduled")  # scheduled, checked_in, checked_out, cancelled
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Package(Base):
    __tablename__ = "packages"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    resident_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tracking_number = Column(String(255), nullable=True)
    carrier = Column(String(100), nullable=True)
    description = Column(String(500), nullable=True)
    locker_code = Column(String(20), nullable=True)
    locker_number = Column(String(50), nullable=True)
    status = Column(String(20), default="received")  # received, notified, picked_up
    received_at = Column(DateTime(timezone=True), default=utc_now)
    notified_at = Column(DateTime(timezone=True), nullable=True)
    picked_up_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    entry_point = Column(String(255), nullable=False)
    access_method = Column(String(50), nullable=False)  # nfc, qr_code, pin, visitor_qr
    direction = Column(String(10), default="entry")  # entry, exit
    device_id = Column(String(100), nullable=True)
    success = Column(Boolean, default=True)
    extra_data = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), default=utc_now)


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    rtsp_url = Column(String(500), nullable=True)
    stream_url = Column(String(500), nullable=True)
    camera_type = Column(String(50), default="fixed")  # fixed, ptz, dome
    zone = Column(String(100), nullable=True)
    status = Column(String(20), default="offline")  # online, offline, error
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    sensor_type = Column(String(50), nullable=False)  # smoke, water_leak, temperature, motion
    location = Column(String(255), nullable=False)
    zone = Column(String(100), nullable=True)
    status = Column(String(20), default="normal")  # normal, alert, offline
    last_reading = Column(JSON, nullable=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class SensorAlert(Base):
    __tablename__ = "sensor_alerts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sensor_id = Column(PGUUID(as_uuid=True), ForeignKey("sensors.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="warning")  # info, warning, critical
    message = Column(Text, nullable=False)
    reading = Column(JSON, nullable=True)
    acknowledged_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class LPREvent(Base):
    __tablename__ = "lpr_events"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    plate_number = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)  # entry, exit
    confidence = Column(Float, default=0.0)
    parking_slot = Column(String(20), nullable=True)
    is_visitor = Column(Boolean, default=True)
    is_stolen_alert = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), default=utc_now)
