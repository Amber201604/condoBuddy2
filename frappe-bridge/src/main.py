"""Frappe Bridge — Sync users and bookings between Core and Frappe/ERPNext.

Runs as a standalone service that:
1. Syncs user data from Core → Frappe
2. Syncs facility bookings bidirectionally
3. Handles webhooks from Frappe
"""
import asyncio
import os
from datetime import datetime

import httpx
from fastapi import FastAPI, Request, HTTPException
import uvicorn

from app.config import settings

app = FastAPI(title="CondoBuddy2 Frappe Bridge")

FRAPPE_BASE = settings.frappe_base_url
FRAPPE_API_KEY = settings.frappe_api_key
FRAPPE_API_SECRET = settings.frappe_api_secret


def frappe_headers():
    return {
        "Authorization": f"token {FRAPPE_API_KEY}:{FRAPPE_API_SECRET}",
        "Content-Type": "application/json",
    }


@app.post("/webhook/user-created")
async def handle_user_created(request: Request):
    """Webhook: New user created in Frappe → sync to Core."""
    data = await request.json()
    # TODO: Call Core API to create/update user
    print(f"[WEBHOOK] User created in Frappe: {data}")
    return {"status": "ok"}


@app.post("/webhook/booking-updated")
async def handle_booking_updated(request: Request):
    """Webhook: Booking updated in Frappe → sync to Core."""
    data = await request.json()
    print(f"[WEBHOOK] Booking updated in Frappe: {data}")
    return {"status": "ok"}


@app.post("/sync/user-to-frappe")
async def sync_user_to_frappe(user_data: dict):
    """Push a user from Core to Frappe."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FRAPPE_BASE}/api/resource/User",
            headers=frappe_headers(),
            json={
                "email": user_data["email"],
                "first_name": user_data.get("full_name", ""),
                "enabled": 1,
                "role_profile_name": user_data.get("role", "Resident"),
            },
        )
        return resp.json()


@app.post("/sync/booking-to-frappe")
async def sync_booking_to_frappe(booking_data: dict):
    """Push a facility booking from Core to Frappe."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FRAPPE_BASE}/api/resource/Facility Booking",
            headers=frappe_headers(),
            json={
                "facility": booking_data["facility_name"],
                "booking_type": booking_data["facility_type"],
                "start_time": booking_data["start_time"],
                "end_time": booking_data["end_time"],
                "resident": booking_data["resident_id"],
                "status": booking_data.get("status", "pending"),
                "attendees": booking_data.get("attendees_count", 1),
            },
        )
        return resp.json()


@app.get("/health")
async def health():
    return {"status": "ok", "frappe_connected": bool(FRAPPE_API_KEY)}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
